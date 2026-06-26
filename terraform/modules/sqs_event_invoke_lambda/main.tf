resource "aws_lambda_event_source_mapping" "this" {
  event_source_arn                   = var.sqs_queue_arn
  function_name                      = var.lambda_function_name
  batch_size                         = var.batch_size
  maximum_batching_window_in_seconds = var.maximum_batching_window_in_seconds
  enabled                            = true
}
