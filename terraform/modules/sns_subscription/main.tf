resource "aws_sns_topic_subscription" "this" {
  topic_arn            = var.sns_topic_arn
  protocol             = "sqs"
  endpoint             = var.queue_arn
  raw_message_delivery = true
}

resource "aws_sqs_queue_policy" "this" {
  queue_url = var.queue_url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = var.queue_arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = var.sns_topic_arn }
      }
    }]
  })
}
