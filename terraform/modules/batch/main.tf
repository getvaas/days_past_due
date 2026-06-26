# Compute environment FARGATE — sin instancias EC2 que gestionar.
resource "aws_batch_compute_environment" "this" {
  name = "${var.name}-compute-env"
  type                     = "MANAGED"
  state                    = "ENABLED"

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = var.max_vcpus
    subnets            = var.subnet_ids
    security_group_ids = var.security_group_ids
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

  container_properties = jsonencode({
    image            = var.ecr_image_uri
    command          = ["python", "-m", "dpd.batch_handler"]
    jobRoleArn       = var.job_role_arn
    executionRoleArn = var.execution_role_arn

    resourceRequirements = [
      { type = "VCPU",   value = var.job_vcpus },
      { type = "MEMORY", value = tostring(var.job_memory) },
    ]

    networkConfiguration = {
      assignPublicIp = "DISABLED"
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-region"        = var.aws_region
        "awslogs-group"         = var.cloudwatch_log_group
        "awslogs-stream-prefix" = "batch"
      }
    }

    environment = [
      for k, v in var.environment_variables : { name = k, value = v }
    ]
  })
}
