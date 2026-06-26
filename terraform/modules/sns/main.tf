locals {
  topic_name = var.fifo_topic ? "${var.name}.fifo" : var.name
}

resource "aws_sns_topic" "this" {
  name                        = local.topic_name
  fifo_topic                  = var.fifo_topic
  content_based_deduplication = var.fifo_topic ? var.content_based_deduplication : false
}
