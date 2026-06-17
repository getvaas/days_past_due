# Topic SNS de entrada (Enricher publica acá; la cola SQS se suscribe).

locals {
  # Los topics FIFO requieren sufijo .fifo
  topic_name = var.fifo_topic ? "${var.environment}_${var.name}_sns_topic.fifo" : "${var.environment}_${var.name}_sns_topic"
}

resource "aws_sns_topic" "sns_topic" {
  name                        = local.topic_name
  display_name                = local.topic_name
  fifo_topic                  = var.fifo_topic
  content_based_deduplication = var.fifo_topic ? var.content_based_deduplication : null
}
