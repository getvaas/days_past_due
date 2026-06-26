locals {
  lambda_policy_statements = length(var.lambda_policy_actions) > 0 ? [
    {
      Action   = var.lambda_policy_actions
      Effect   = "Allow"
      Resource = "*"
    }
  ] : var.lambda_policy_statements

  has_inline_policy = length(local.lambda_policy_statements) > 0
}

resource "aws_iam_role" "iam_role_lambda" {
  name = var.lambda_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "iam_policy_lambda" {
  count       = local.has_inline_policy ? 1 : 0
  name        = var.lambda_policy_name
  path        = "/"
  description = var.lambda_policy_name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.lambda_policy_statements
  })
}

resource "aws_iam_role_policy_attachment" "lambda_iam_policy_attachment_to_lambda_iam_role" {
  count      = local.has_inline_policy ? 1 : 0
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = aws_iam_policy.iam_policy_lambda[0].arn
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  count      = var.attach_basic_execution ? 1 : 0
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "vpc_access" {
  count      = var.attach_vpc_access ? 1 : 0
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
