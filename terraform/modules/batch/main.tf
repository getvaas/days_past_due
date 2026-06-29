data "aws_region" "current" {}

locals {
  job_role_name       = coalesce(var.job_role_name, "${var.name}-job-role")
  job_policy_name     = coalesce(var.job_policy_name, "${var.name}-job-policy")
  execution_role_name = coalesce(var.execution_role_name, "${var.name}-execution-role")
  log_group_name      = coalesce(var.cloudwatch_log_group_name, "/aws/batch/${var.name}")
  retention_in_days   = coalesce(var.log_retention_in_days, var.environment == "prod" ? 30 : 7)

  resolved_subnet_ids         = length(var.subnet_ids) > 0 ? var.subnet_ids: []
  resolved_security_group_ids = length(var.security_group_ids) > 0 ? var.security_group_ids : []
}

resource "aws_iam_role" "job_role" {
  name = local.job_role_name
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
  name        = local.job_policy_name
  path        = "/"
  description = local.job_policy_name
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
  name = local.execution_role_name
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

# Log group donde el job escribe vía el driver awslogs. El módulo lo crea para
# ser self-contained: AmazonECSTaskExecutionRolePolicy ya da permisos de
# escritura, pero el grupo tiene que existir o el awslogs driver falla.
resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group_name
  retention_in_days = local.retention_in_days
}

# Compute environment FARGATE — sin instancias EC2 que gestionar.
resource "aws_batch_compute_environment" "this" {
  name  = "${var.name}-compute-env"
  type  = "MANAGED"
  state = "ENABLED"

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = var.max_vcpus
    subnets            = local.resolved_subnet_ids
    security_group_ids = local.resolved_security_group_ids
  }
}

# Job queue asociada al compute environment.
resource "aws_batch_job_queue" "this" {
  name     = "${var.name}-job-queue"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.this.arn
  }
}

# Job definition con la imagen Docker del batch handler.
resource "aws_batch_job_definition" "this" {
  name = "${var.name}-job-definition"
  type = "container"

  platform_capabilities = ["FARGATE"]

  # AWS normalizes the stored JSON (adds defaults, reorders keys), causing
  # perpetual drift on every plan. Since Batch Fargate pulls :latest at
  # job-run time, updating this on every deploy would only create unnecessary
  # new revisions and invalidate the ARN stored in Lambda's env vars.
  lifecycle {
    ignore_changes = [container_properties]
  }

  container_properties = jsonencode({
    image            = var.ecr_image_uri
    command          = ["python", "-m", "dpd.batch_handler"]
    jobRoleArn       = aws_iam_role.job_role.arn
    executionRoleArn = aws_iam_role.execution_role.arn

    resourceRequirements = [
      { type = "VCPU", value = var.job_vcpus },
      { type = "MEMORY", value = tostring(var.job_memory) },
    ]

    networkConfiguration = {
      assignPublicIp = "DISABLED"
    }

    runtimePlatform = {
      cpuArchitecture       = upper(try(var.architectures[0], "X86_64"))
      operatingSystemFamily = "LINUX"
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-region"        = data.aws_region.current.region
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-stream-prefix" = "batch"
      }
    }

    environment = [
      for k, v in var.environment_variables : { name = k, value = v }
    ]
  })
}
