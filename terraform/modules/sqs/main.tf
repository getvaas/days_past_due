# Cola SQS de entrada + DLQ + redrive + alarmas.
# Autocontenido: no depende de ningún módulo externo.

resource "aws_sqs_queue" "dead_letter_queue" {
  count                       = var.avoid_dl_queue ? 0 : 1
  name                        = local.dl_queue_name
  max_message_size            = var.max_message_size
  message_retention_seconds   = var.message_retention_seconds
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : null
}

resource "aws_sqs_queue" "queue" {
  name                        = local.queue_name
  max_message_size            = var.max_message_size
  message_retention_seconds   = var.message_retention_seconds
  visibility_timeout_seconds  = var.visibility_timeout
  fifo_queue                  = var.fifo_queue
  content_based_deduplication = var.fifo_queue ? var.content_based_deduplication : null
}

resource "aws_sqs_queue_redrive_policy" "queue_redrive_policy" {
  count     = var.avoid_dl_queue ? 0 : 1
  queue_url = aws_sqs_queue.queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter_queue[0].arn
    maxReceiveCount     = var.max_receive_count
  })
}

# Alarmas: solo si se provee un topic de alarmas (var.sns_alarms_topic_arn != "").
resource "aws_cloudwatch_metric_alarm" "sqs_avg_age_old_msg" {
  count               = local.activate_alarm
  alarm_name          = "${aws_sqs_queue.queue.name}_avg_age_old_msg"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Average"
  threshold           = 60 + aws_sqs_queue.queue.message_retention_seconds
  alarm_description   = "Avg age oldest message."
  alarm_actions       = [var.sns_alarms_topic_arn]
  dimensions = {
    QueueName = aws_sqs_queue.queue.name
  }
}

resource "aws_cloudwatch_metric_alarm" "dl_sqs_avg_age_old_msg" {
  count               = var.avoid_dl_queue ? 0 : local.activate_alarm
  alarm_name          = "${aws_sqs_queue.dead_letter_queue[0].name}_dl_avg_age_old_msg"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 120
  statistic           = "Average"
  threshold           = 86400
  alarm_description   = "Avg age oldest message."
  alarm_actions       = [var.sns_alarms_topic_arn]
  dimensions = {
    QueueName = aws_sqs_queue.dead_letter_queue[0].name
  }
}
