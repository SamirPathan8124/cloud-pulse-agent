resource "aws_cloudwatch_dashboard" "pulse" {
  dashboard_name = "cloud-pulse"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title   = "EC2 CPU (average, 5 min)"
          region  = "us-east-1"
          view    = "timeSeries"
          period  = 300
          metrics = [[{ expression = "SEARCH('{AWS/EC2,InstanceId} MetricName=\"CPUUtilization\"', 'Average', 300)", id = "e1" }]]
        }
      },
      {
        type = "alarm", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "Alarm state"
          alarms = ["arn:aws:cloudwatch:us-east-1:${data.aws_caller_identity.me.account_id}:alarm:cloud-pulse-web-cpu-high"]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "SQS queue depth (alerts vs DLQ)"
          region = "us-east-1"
          view   = "timeSeries"
          period = 300
          stat   = "Maximum"
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "cloud-pulse-alerts"],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "cloud-pulse-alerts-dlq"]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6
        properties = {
          title   = "Alerts received"
          region  = "us-east-1"
          view    = "timeSeries"
          period  = 300
          stat    = "Sum"
          metrics = [["AWS/SQS", "NumberOfMessagesSent", "QueueName", "cloud-pulse-alerts"]]
        }
      }
    ]
  })
}
