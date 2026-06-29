locals {
  global_timeout           = 900
  cloudwatch_configuration = {
    log_group_name    = "/aws/lambda/${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-lambda"
    retention_in_days = var.environment == "dev" ? 1 : 7
  }
  lambda_configuration = {
    name           = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-lambda"
    handler        = "lambda_handler.lambda_handler"
    memory_size    = "1024"
    architectures  = ["arm64"]
    iam_configuration = {
      role_lambda_name      = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-lambda-role"
      policy_lambda_name    = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-lambda-policy"
      policy_lambda_actions = [
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "secretsmanager:GetSecretValue",
        "sqs:DeleteMessage",
        "sqs:ReceiveMessage",
        "sqs:GetQueueAttributes",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "ssm:GetParameter",
        "sns:Publish"
      ]
    }
  }
    batch_configuration = {
    name           = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-lambda"
    memory_size    = "2048"
    v_cpus = 2
    architectures  = ["arm64"]
    iam_configuration = {
      role_batch_name      = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-batch-role"
      policy_batch_name    = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}-batch-policy"
      policy_batch_actions = [
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "secretsmanager:GetSecretValue",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "ssm:GetParameter",
        "sns:Publish"
      ]
    }
  }
  sqs_configuration = {
    name = "${var.environment}-${replace(var.project_name_snake_case,"_" ,"-")}"
    visibility_timeout = 60
    message_retention_seconds = 60
  }
  secrets_manager_configuration = {
    keys = [

    ]
  }
}
