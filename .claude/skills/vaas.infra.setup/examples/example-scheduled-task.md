# Ejemplo: ECS Scheduled Task (Cron Job)

Este ejemplo muestra la infraestructura para una tarea ECS programada que se ejecuta en un schedule, con acceso a base de datos y S3.

---

## Contexto

- **Tarea**: `report-generator` — genera reportes diarios
- **Stack**: Node.js (contenedor Docker)
- **Schedule**: Todos los días a las 6 AM UTC
- **Recursos adicionales**: S3 (output de reportes), Secrets Manager (DB credentials)

---

## `deploy/terraform/main.tf`

```hcl
data "aws_secretsmanager_secret" "db_credentials" {
  arn = var.db_credentials_secret_manager
}

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

module "ecr" {
  source = "git@github.com:getvaas/tf_modules.git//ecr"
  name   = "${var.environment}-report-generator-repository"
}

module "scheduled_task" {
  source              = "git@github.com:getvaas/tf_modules.git//ecs_task"
  environment         = var.environment
  aws_region          = var.aws_region
  ecs_task_name       = "${var.environment}-report-generator"
  ecs_cpu_millis_min  = 1024
  ecs_memory_min      = 2048
  ecr_repository_uri  = module.ecr.ecr_repository_uri
  schedule_expression = "cron(0 6 * * ? *)"
  arm_service         = true
  capacity_provider   = var.capacity_provider
  ecs_policy_actions = [
    "ecr:GetAuthorizationToken",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "secretsmanager:GetSecretValue",
    "s3:PutObject",
    "s3:GetObject"
  ]
  secrets = {
    "DB_HOST"     = "${var.db_credentials_secret_manager}:host::"
    "DB_USERNAME" = "${var.db_credentials_secret_manager}:username::"
    "DB_PASSWORD" = "${var.db_credentials_secret_manager}:password::"
  }
  environment_variables = {
    "ENVIRONMENT"    = var.environment
    "REPORTS_BUCKET" = module.s3.bucket_name
    "NODE_ENV"       = var.environment == "prod" ? "production" : "development"
  }

  depends_on = [module.ecr]
}

module "s3" {
  source = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name = "report-generator-output"
  environment = var.environment
}

module "cloudwatch" {
  source         = "git@github.com:getvaas/tf_modules.git//cloudwatch"
  log_group_name = "ecs/${var.environment}/report-generator"
  environment    = var.environment
}
```

---

## `deploy/terraform/inputs.tf`

```hcl
variable "environment" { type = string }
variable "aws_region" { type = string }

# Naming
variable "project_name_camel_case" { type = string }
variable "component_name_camel_case" { type = string }

# Metadata
variable "author" { type = string }
variable "cost_center" { type = string }
variable "github_repository" { type = string }

# ECS
variable "capacity_provider" { type = string }

# Secrets
variable "db_credentials_secret_manager" { type = string }

# AWS Profile
variable "profile" {
  type    = string
  default = ""
}
```

---

## `deploy/terraform/configuration/dev/vars.tfvars`

```hcl
environment                   = "dev"
aws_region                    = "us-east-1"
project_name_camel_case       = "ReportGenerator"
component_name_camel_case     = "Task"
author                        = "team@getvaas.com"
cost_center                   = "ReportGenerator"
github_repository             = "report-generator"
capacity_provider             = "dev_arm_large_one_cluster_capacity_provider"
db_credentials_secret_manager = "arn:aws:secretsmanager:us-east-1:052650215423:secret:dev-report-generator-XXXXXX"
```

---

## `deploy/terraform/configuration/dev/backend.conf`

```
bucket         = "<prefix>-dev-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "dev-terraform-lock-table"
key            = "report-generator/terraform.tfstate"
```

---

## Notas

- El `ecs_task` auto-resuelve el cluster (`<env>-one-cluster`) y crea el log group automáticamente
- `schedule_expression` usa formato cron de AWS: `cron(minutos horas día-del-mes mes día-de-la-semana año)`
- `arm_service = true` usa instancias ARM (más baratas), `false` usa x86
- El ECR se crea separado porque `ecs_task` no auto-crea ECR (a diferencia de `ecs_service`)
