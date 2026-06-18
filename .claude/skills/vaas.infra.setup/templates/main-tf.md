# Template: main.tf

El archivo principal que orquesta todos los módulos de Terraform.

## Template

```hcl
# =============================================================================
# Data Sources (opcional — solo si el proyecto necesita secretos)
# =============================================================================
# data "aws_secretsmanager_secret" "{{secret_name}}" {
#   arn = var.{{secret_name}}_secret_manager
# }
# data "aws_secretsmanager_secret_version" "{{secret_name}}_current" {
#   secret_id = data.aws_secretsmanager_secret.{{secret_name}}.id
# }

# =============================================================================
# Backend y Provider
# =============================================================================
terraform {
  backend "s3" {}
}

provider "aws" {
  region  = var.aws_region
  profile = var.profile
  default_tags {
    tags = {
      Environment   = var.environment
      Author        = var.author
      CostCenter    = var.cost_center
      ProjectName   = var.project_name_camel_case
      ComponentName = var.component_name_camel_case
      GithubRepo    = var.github_repository
    }
  }
}

# =============================================================================
# IAM
# =============================================================================
module "iam_orchestrator" {
  source           = "./iam"
  iam_orchestrator = local.iam_orchestrator
}

# =============================================================================
# ECR
# =============================================================================
module "ecr_orchestrator" {
  source           = "./ecr"
  ecr_orchestrator = local.ecr_orchestrator
}

# =============================================================================
# ECS Service (usar tf_modules//ecs_service)
# =============================================================================
module "ecs_service" {
  source                    = "git@github.com:getvaas/tf_modules.git//ecs_service"
  ecs_role_arn              = module.iam_orchestrator.ecs_role_arn
  ecs_memory_min            = local.ecs_cluster_configuration.memory
  ecs_cpu_millis_min        = local.ecs_cluster_configuration.cpu
  ecr_repository_uri        = module.ecr_orchestrator.ecr_repository_uri
  ecs_service_name          = "${var.environment}-{{service_name}}"
  container_port            = local.target_group_configuration.port
  environment               = var.environment
  health_check_path         = local.target_group_configuration.health_check_path
  # secrets = { ... }        # Agregar si el servicio necesita secretos
  environment_variables = merge(var.environment_variables, {
    "AWS_REGION"             = var.aws_region
    "ENVIRONMENT"            = var.environment
  })
  add_telemetry             = true
  cloudwatch_log_group_name = local.cloudwatch_configuration.log_group_name
  sns_alarms_topic_arn      = var.sns_alarms_topic_arn
  capacity_provider         = var.capacity_provider
  lb_listener_rules = [{
    priority    = {{priority}}
    action_type = "forward"
    conditions  = [{ field = "path_pattern", values = ["{{path_pattern}}"] }]
  }]
  enable_internal_routing = true
  enable_public_routing   = true

  depends_on = [module.iam_orchestrator, module.ecr_orchestrator]
}

# =============================================================================
# Módulos adicionales (agregar según necesidad)
# =============================================================================
# module "s3" { ... }
# module "sqs" { ... }
# module "parameter_store" { ... }
```

## Variables a reemplazar

| Placeholder | Descripción | Ejemplo |
|------------|-------------|---------|
| `{{service_name}}` | Nombre del servicio | `documents-api` |
| `{{priority}}` | Prioridad de la regla del ALB (1-50000) | `5000` |
| `{{path_pattern}}` | Path pattern para el ALB | `/api/documents/v2/*` |
| `{{secret_name}}` | Nombre del secret | `api_credentials` |
