resource "aws_lambda_permission" "sqs_lambda_function_permission" {
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = var.sqs_queue_arn
}
resource "aws_lambda_event_source_mapping" "lambda_function_source_mapping_to_queue" {
  event_source_arn = var.sqs_queue_arn
  enabled          = true
  function_name    = var.lambda_function_name
  batch_size       = 1
}