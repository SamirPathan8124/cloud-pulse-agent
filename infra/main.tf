data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "web" {
  ami           = data.aws_ssm_parameter.al2023.value
  instance_type = "t3.small"
  tags          = { Name = "cloud-pulse-web" }
  lifecycle {
    ignore_changes = [ami]
  }
}


resource "aws_sns_topic" "alerts" {
  name = "cloud-pulse-alerts"
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "cloud-pulse-web-cpu-high"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.web.id }
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
