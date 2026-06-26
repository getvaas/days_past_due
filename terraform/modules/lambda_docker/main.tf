resource "aws_lambda_function" "lambda_function" {
  package_type  = "Image"
  function_name = var.name
  role          = var.iam_role_lambda_arn
  image_uri     = "${var.ecr_repository_uri}:${var.image_tag}"
  timeout       = var.timeout
  memory_size   = var.memory_size
  reserved_concurrent_executions = var.reserved_concurrent_executions

  ephemeral_storage {
    size = var.ephemeral_storage
  }

  environment {
    variables = var.environment_variables
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}
