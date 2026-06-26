resource "aws_iam_role" "iam_role_lambda" {
  name = var.iam_configuration.role_lambda_name
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
  name        = var.iam_configuration.policy_lambda_name
  path        = "/"
  description = var.iam_configuration.policy_lambda_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = var.iam_configuration.policy_lambda_actions
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "attachment" {
  role       = aws_iam_role.iam_role_lambda.name
  policy_arn = aws_iam_policy.iam_policy_lambda.arn
  depends_on = [aws_iam_role.iam_role_lambda, aws_iam_policy.iam_policy_lambda]
}
