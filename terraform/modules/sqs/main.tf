locals {
  queue_suffix = var.fifo_queue ? ".fifo" : ""
  queue_name   = "${var.name}${local.queue_suffix}"
  dlq_name     = "${var.name}_dlq${local.queue_suffix}"
}

resource "aws_sqs_queue" "dlq" {
  name                        = local.dlq_name
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : false
  message_retention_seconds   = var.message_retention_seconds
}

resource "aws_sqs_queue" "this" {
  name                        = local.queue_name
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : false
  visibility_timeout_seconds  = var.visibility_timeout
  message_retention_seconds   = var.message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  count               = var.sns_alarms_topic_arn != "" ? 1 : 0
  alarm_name          = "${local.dlq_name}-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [var.sns_alarms_topic_arn]

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}
