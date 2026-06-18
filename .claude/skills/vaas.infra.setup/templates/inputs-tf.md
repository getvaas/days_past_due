# Template: inputs.tf

Define todas las variables de entrada del root module. Los valores se pasan desde los archivos `.tfvars`.

## Template

```hcl
# =============================================================================
# Infraestructura
# =============================================================================
variable "environment" {
  type        = string
  description = "Environment name: dev, stg, prod"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

# =============================================================================
# Naming (usado en tags y nombres de recursos)
# =============================================================================
variable "project_name_camel_case" {
  type        = string
  description = "Project name in CamelCase, e.g. MyProject"
}

variable "project_name_snake_case" {
  type        = string
  description = "Project name in snake_case, e.g. my_project"
}

variable "project_name_acronym_snake_case" {
  type        = string
  description = "Project name acronym in snake_case, e.g. my_project"
}

variable "component_name_camel_case" {
  type        = string
  description = "Component name in CamelCase, e.g. Api"
}

variable "component_name_snake_case" {
  type        = string
  description = "Component name in snake_case, e.g. api"
}

# =============================================================================
# Metadata (usado en tags)
# =============================================================================
variable "author" {
  type        = string
  description = "Author email"
}

variable "cost_center" {
  type        = string
  description = "Cost center for billing"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name"
}

# =============================================================================
# ALB y ECS (solo para servicios web/API)
# =============================================================================
variable "listener_https_arn" {
  type        = string
  description = "ARN of the ALB HTTPS listener"
}

variable "capacity_provider" {
  type        = string
  description = "ECS capacity provider name"
}

# =============================================================================
# Alarms
# =============================================================================
variable "sns_alarms_topic_arn" {
  type        = string
  description = "ARN of the SNS topic for CloudWatch alarms"
}

# =============================================================================
# Environment variables (específicas por ambiente)
# =============================================================================
variable "environment_variables" {
  type        = map(any)
  description = "Environment variables for the container"
  default     = {}
}

# =============================================================================
# AWS Profile (solo para ejecución local)
# =============================================================================
variable "profile" {
  type        = string
  description = "AWS CLI profile name (empty for CI/CD)"
  default     = ""
}

# =============================================================================
# Secrets (agregar según necesidad del proyecto)
# =============================================================================
# variable "api_credentials_secret_manager" {
#   type        = string
#   description = "ARN of the Secrets Manager secret"
# }
```

## Notas

- Incluir `listener_https_arn` y `capacity_provider` solo si el servicio es una API/web detrás de ALB
- Agregar variables de Secrets Manager según los secretos que necesite el servicio
- `environment_variables` es un map que se pasa desde `vars.tfvars` y se mergea en `main.tf`
- `profile` se deja vacío por defecto — solo se usa para ejecución local con AWS CLI configurado
