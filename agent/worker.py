import os, json, time, threading
from contextlib import asynccontextmanager
import boto3
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
QUEUE_URL = os.getenv("QUEUE_URL")
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"
sqs = boto3.client("sqs", region_name="us-east-1")
stats = {"processed": 0, "failed": 0, "skipped": 0, "last_alert": None}


class TokenBucket:
    def __init__(self, capacity=3, refill_seconds=60):
        self.capacity, self.refill = capacity, refill_seconds
        self.tokens, self.last = capacity, time.time()

    def take(self):
        while True:
            now = time.time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) / self.refill)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            time.sleep(2)


bucket = TokenBucket()


def to_alert(body):
    env = json.loads(body)
    msg = json.loads(env["Message"]) if "Message" in env else env
    if msg.get("NewStateValue") != "ALARM":
        return None
    return f"{msg.get('AlarmName')}: {msg.get('NewStateReason')}"


def handle(alert):
    if DRY_RUN:
        print("[dry-run] would run agent for:", alert, flush=True)
        return
    from graph import app as agent
    from pr import open_pr
    r = agent.invoke({"alert": alert})
    if not r["review"].get("approved"):
        print("[agent] reviewer rejected:", r["review"], flush=True)
        return
    new = r["proposed"]
    if not new.endswith("\n"):
        new += "\n"
    print("[agent] PR created:", open_pr("infra/main.tf", new, alert, r["triage"], r["memory"], r["review"]), flush=True)


def poll_loop():
    while True:
        try:
            resp = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20)
            for m in resp.get("Messages", []):
                try:
                    alert = to_alert(m["Body"])
                    if alert:
                        bucket.take()
                        stats["last_alert"] = alert
                        handle(alert)
                        stats["processed"] += 1
                    else:
                        stats["skipped"] += 1
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=m["ReceiptHandle"])
                except Exception as e:
                    stats["failed"] += 1
                    print("[worker] failed, will retry then go to DLQ:", e, flush=True)
        except Exception as e:
            print("[worker] poll error:", e, flush=True)
            time.sleep(5)


@asynccontextmanager
async def lifespan(_):
    threading.Thread(target=poll_loop, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "dry_run": DRY_RUN, **stats}
