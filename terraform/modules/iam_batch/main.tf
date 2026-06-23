# Rol que asume el contenedor del job: acceso a S3, SNS, Secrets Manager, SQS.
resource "aws_iam_role" "job_role" {
  name = var.job_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "job_policy" {
  name = var.job_policy_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = var.job_policy_actions
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "job_attachment" {
  role       = aws_iam_role.job_role.name
  policy_arn = aws_iam_policy.job_policy.arn
}

# Rol de ejecución ECS: pull de ECR + escritura en CloudWatch (gestionado por AWS Batch).
resource "aws_iam_role" "execution_role" {
  name = var.execution_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
