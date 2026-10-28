import os, sys, json, datetime as dt
import boto3
from dotenv import load_dotenv

load_dotenv()
REGION = "us-east-1"
ec2 = boto3.client("ec2", region_name=REGION)
cw = boto3.client("cloudwatch", region_name=REGION)
sqs = boto3.client("sqs", region_name=REGION)
QUEUE_URL = (os.getenv("QUEUE_URL") or "").strip()
IDLE_CPU = float(os.getenv("IDLE_CPU", "10"))
# approx on-demand Linux prices, us-east-1, USD per hour
PRICE = {"t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208,
         "t3.medium": 0.0416, "t3.large": 0.0832}


def avg_cpu(instance_id, hours=24):
    end = dt.datetime.now(dt.timezone.utc)
    r = cw.get_metric_statistics(
        Namespace="AWS/EC2", MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=end - dt.timedelta(hours=hours), EndTime=end,
        Period=3600, Statistics=["Average"])
    pts = [p["Average"] for p in r["Datapoints"]]
    return sum(pts) / len(pts) if pts else None


def scan():
    found = []
    res = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": ["cloud-pulse-web"]},
        {"Name": "instance-state-name", "Values": ["running"]}])
    for r in res["Reservations"]:
        for i in r["Instances"]:
            cpu = avg_cpu(i["InstanceId"])
            monthly = PRICE.get(i["InstanceType"], 0) * 730
            found.append((i["InstanceId"], i["InstanceType"], cpu, monthly))
    return found


if __name__ == "__main__":
    send = "--send" in sys.argv
    for iid, itype, cpu, monthly in scan():
        cpu_txt = "no data yet" if cpu is None else f"{cpu:.1f}%"
        print(f"{iid} | {itype} | avg CPU 24h: {cpu_txt} | approx ${monthly:.2f}/month")
        if cpu is not None and cpu < IDLE_CPU:
            reason = (f"FinOps: cloud-pulse-web ({itype}) averaged {cpu:.1f}% CPU over 24h, "
                      f"below {IDLE_CPU:.0f}%. Approx cost ${monthly:.2f}/month. "
                      f"Consider rightsizing to a smaller instance type.")
            print("[finops] idle detected:", reason)
            if send:
                sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps({
                    "AlarmName": "finops-idle-instance",
                    "NewStateValue": "ALARM",
                    "NewStateReason": reason}))
                print("[finops] alert sent to SQS")
