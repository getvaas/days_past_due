# Suscripción SNS -> SQS + policy que permite a SNS enviar a la cola.

resource "aws_sns_topic_subscription" "sns_topic_subscription" {
  endpoint             = var.queue_arn
  protocol             = "sqs"
  topic_arn            = var.sns_topic_arn
  raw_message_delivery = true
}

resource "aws_sqs_queue_policy" "sns_queue_policy" {
  queue_url = var.queue_url
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "sqspolicy"
    Statement = [
      {
        Sid       = "AllowSNSPublish"
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = var.queue_arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = var.sns_topic_arn
          }
        }
      }
    ]
  })
  depends_on = [aws_sns_topic_subscription.sns_topic_subscription]
}
