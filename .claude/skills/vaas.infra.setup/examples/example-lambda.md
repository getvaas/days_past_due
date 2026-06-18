# Ejemplo: Lambda Function con EventBridge Schedule

Este ejemplo muestra la infraestructura para una Lambda function que se ejecuta en un schedule (cron), con acceso a S3 y Parameter Store.

---

## Contexto

- **Función**: `data-sync` — sincroniza datos diariamente
- **Runtime**: Python 3.11
- **Schedule**: Todos los días a las 2 AM UTC
- **Recursos adicionales**: S3 (lectura), Parameter Store (configuración)

---

## `deploy/terraform/main.tf`

```hcl
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

module "iam_lambda" {
  source = "git@github.com:getvaas/tf_modules.git//iam_lambda"
  iam_configuration = {
    role_lambda_name      = "${var.environment}-data-sync-lambda-role"
    policy_lambda_name    = "${var.environment}-data-sync-lambda-policy"
    policy_lambda_actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "s3:GetObject",
      "s3:ListBucket",
      "ssm:GetParametersByPath"
    ]
  }
}

module "lambda" {
  source              = "git@github.com:getvaas/tf_modules.git//lambda"
  name                = "${var.environment}-data-sync"
  handler             = "index.handler"
  runtime             = "python3.11"
  memory_size         = 512
  timeout             = 300
  architectures       = ["arm64"]
  iam_role_lambda_arn = module.iam_lambda.iam_role_lambda_arn
  s3_code_bucket      = var.lambda_code_bucket
  s3_code_key         = "data-sync/latest.zip"
  environment_variables = {
    "ENVIRONMENT"  = var.environment
    "SOURCE_BUCKET" = var.source_bucket_name
  }

  depends_on = [module.iam_lambda]
}

module "daily_trigger" {
  source              = "git@github.com:getvaas/tf_modules.git//eventbridge_invoke_lambda"
  name                = "${var.environment}-data-sync-daily"
  lambda_arn          = module.lambda.lambda_function_arn
  lambda_name         = module.lambda.lambda_function_name
  schedule_expression = "cron(0 2 * * ? *)"

  depends_on = [module.lambda]
}

module "parameter_store" {
  source = "git@github.com:getvaas/tf_modules.git//parameter_store"
  prefix = "/${var.environment}/data-sync"
  parameter_store_configuration = {
    "api_url"     = var.api_url
    "max_retries" = "3"
    "timeout_ms"  = "5000"
  }
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

# Lambda specific
variable "lambda_code_bucket" { type = string }
variable "source_bucket_name" { type = string }
variable "api_url" { type = string }

# AWS Profile
variable "profile" {
  type    = string
  default = ""
}
```

---

## `deploy/terraform/configuration/dev/vars.tfvars`

```hcl
environment              = "dev"
aws_region               = "us-east-1"
project_name_camel_case  = "DataSync"
component_name_camel_case = "Lambda"
author                   = "team@getvaas.com"
cost_center              = "DataSync"
github_repository        = "data-sync"
lambda_code_bucket       = "dev-lambda-deployments"
source_bucket_name       = "dev-data-source"
api_url                  = "https://dev.api.getvaas.com"
```

---

## `deploy/terraform/configuration/dev/backend.conf`

```
bucket         = "<prefix>-dev-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "dev-terraform-lock-table"
key            = "data-sync/terraform.tfstate"
```
