# Ejemplo: ECS Service — API Java/Spring (como project-name)

Este ejemplo muestra la infraestructura completa para una API Java/Spring Boot corriendo en ECS, con S3, SQS/SNS, y secretos de Secrets Manager.

---

## Contexto

- **Servicio**: `project-name` — API REST de documentos
- **Stack**: Java 17 + Spring Boot + Gradle
- **Puerto**: 80 (dentro del contenedor)
- **Path del ALB**: `/api/project-name/*`
- **Recursos adicionales**: S3 (almacenamiento), SQS/SNS (eventos), Secrets Manager (DB credentials, API keys)

---

## `deploy/terraform/main.tf`

```hcl
# Data Sources — Leer secretos de Secrets Manager
data "aws_secretsmanager_secret" "api_credentials" {
  arn = var.api_credentials_secret_manager
}
data "aws_secretsmanager_secret_version" "api_credentials_current" {
  secret_id = data.aws_secretsmanager_secret.api_credentials.id
}

# Backend y Provider
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

# Módulos
module "iam_orchestrator" {
  source           = "git@github.com:getvaas/tf_modules.git//iam"
  iam_orchestrator = local.iam_orchestrator
}

module "ecr_orchestrator" {
  source           = "git@github.com:getvaas/tf_modules.git//ecr"
  ecr_orchestrator = local.ecr_orchestrator
}

module "ecs_service" {
  source                    = "git@github.com:getvaas/tf_modules.git//ecs_service"
  ecs_role_arn              = module.iam_orchestrator.ecs_role_arn
  ecs_memory_min            = local.ecs_cluster_configuration.memory
  ecs_cpu_millis_min        = local.ecs_cluster_configuration.cpu
  ecr_repository_uri        = module.ecr_orchestrator.ecr_repository_uri
  ecs_service_name          = "${var.environment}-project-name"
  container_port            = local.target_group_configuration.port
  environment               = var.environment
  health_check_path         = local.target_group_configuration.health_check_path
  secrets = {
    "DATASOURCE_HOST"     = "${var.api_credentials_secret_manager}:host::"
    "DATASOURCE_USERNAME" = "${var.api_credentials_secret_manager}:username::"
    "DATASOURCE_PASSWORD" = "${var.api_credentials_secret_manager}:password::"
  }
  environment_variables = merge(var.environment_variables, {
    "AWS_REGION"             = var.aws_region
    "SPRING_PROFILES_ACTIVE" = var.environment
    "ENVIRONMENT"            = var.environment
    "DOCUMENTS_BUCKET"       = module.s3.bucket_name
    "EVENTS_TOPIC_ARN"       = module.events_queue.sns_topic_arn
  })
  add_telemetry             = true
  cloudwatch_log_group_name = local.cloudwatch_configuration.log_group_name
  sns_alarms_topic_arn      = var.sns_alarms_topic_arn
  capacity_provider         = var.capacity_provider
  lb_listener_rules = [{
    priority    = 2
    action_type = "forward"
    conditions  = [{ field = "path_pattern", values = ["/api/documents/v2/*"] }]
  }]
  enable_internal_routing = true
  enable_public_routing   = true

  depends_on = [module.iam_orchestrator, module.ecr_orchestrator]
}

module "s3" {
  source        = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name   = "project-name"
  bucket_prefix = "gf78999f"
  environment   = var.environment
}

module "events_queue" {
  source               = "git@github.com:getvaas/tf_modules.git//sns_sqs"
  name                 = replace("${local.name}-events", "-", "_")
  visibility_timeout   = 1800
  max_receive_count    = 10
  message_retention_seconds = 86400
  environment          = var.environment
  sns_alarms_topic_arn = var.sns_alarms_topic_arn
}
```

---

## `deploy/terraform/inputs.tf`

```hcl
variable "environment" { type = string }
variable "environment_full_name" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }

# Naming
variable "project_name_camel_case" { type = string }
variable "project_name_snake_case" { type = string }
variable "project_name_acronym_snake_case" { type = string }
variable "component_name_camel_case" { type = string }
variable "component_name_snake_case" { type = string }

# Metadata
variable "author" { type = string }
variable "cost_center" { type = string }
variable "github_repository" { type = string }

# ALB
variable "listener_https_arn" { type = string }
variable "capacity_provider" { type = string }

# Secrets
variable "api_credentials_secret_manager" { type = string }

# Alarms
variable "sns_alarms_topic_arn" { type = string }

# Environment variables por ambiente
variable "environment_variables" { type = map(any) }

# AWS Profile (vacío por defecto, solo para local)
variable "profile" {
  type    = string
  default = ""
}
```

---

## `deploy/terraform/locals.tf`

```hcl
locals {
  name = "${var.environment}-${var.project_name_snake_case}"

  iam_orchestrator = {
    role_ecs_name   = "${var.environment}-project-name-ecs-role"
    policy_ecs_name = "${var.environment}-project-name-ecs-policy"
    ecs_policy_actions = [
      "ecr:GetAuthorizationToken",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
      "secretsmanager:GetSecretValue",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
      "s3:DeleteObject",
      "ssm:GetParametersByPath",
      "sns:Publish"
    ]
  }

  ecr_orchestrator = {
    name = "${var.environment}-project-name-repository"
  }

  ecs_cluster_configuration = {
    memory  = 3072
    cpu     = "2048"
    version = "v1.0.0"
  }

  target_group_configuration = {
    port              = "80"
    prefix_path       = "/api/documents/v2"
    health_check_path = "/api/documents/v2/actuator/health"
  }

  cloudwatch_configuration = {
    log_group_name    = "ecs/${var.environment}/${var.project_name_snake_case}/${var.component_name_snake_case}"
    log_stream_name   = "log"
    retention_in_days = var.environment == "dev" ? 1 : 7
  }
}
```

---

## `deploy/terraform/configuration/global.tfvars`

```hcl
project_name_camel_case         = "Documents"
project_name_snake_case         = "documents"
project_name_acronym_snake_case = "documents"
component_name_camel_case       = "Api"
component_name_snake_case       = "api"
author                          = "team@getvaas.com"
cost_center                     = "ProjectName"
github_repository               = "project-name"
```

---

## `deploy/terraform/configuration/dev/vars.tfvars`

```hcl
environment           = "dev"
environment_full_name = "Development"
aws_region            = "us-east-1"
vpc_id                = "vpc-0fb53b76f02cbe650"
listener_https_arn    = "arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Dev-Pub-AppLoadBalancer/7bac3213d92ada71/49839fb562ea4760"
capacity_provider     = "dev_arm_large_one_cluster_capacity_provider"
sns_alarms_topic_arn  = "arn:aws:sns:us-east-1:052650215423:dev-borbotones-alarms-topic"
api_credentials_secret_manager = "arn:aws:secretsmanager:us-east-1:052650215423:secret:dev-project-name-secret-manager-XXXXXX"

environment_variables = {
  SERVER_PORT          = "80"
  SERVER_CONTEXT_PATH  = "/api/documents/v2"
}
```

---

## `deploy/terraform/configuration/dev/backend.conf`

```
bucket         = "6fc5w786-dev-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "dev-terraform-lock-table"
key            = "project-name/terraform.tfstate"
```
