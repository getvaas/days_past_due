resource "aws_iam_role" "job_role" {
  name = var.job_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "job_policy" {
  name        = var.job_policy_name
  path        = "/"
  description = var.job_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = var.job_policy_actions
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "job_policy_attachment" {
  role       = aws_iam_role.job_role.name
  policy_arn = aws_iam_policy.job_policy.arn
}

resource "aws_iam_role" "execution_role" {
  name = var.execution_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
