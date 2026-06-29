# Template: locals.tf

Define configuración computada que se pasa a los módulos. Centraliza valores que dependen de variables.

## Template

```hcl
locals {
  # Nombre base: <env>-<project>
  name = "${var.environment}-${var.project_name_snake_case}"

  # ==========================================================================
  # IAM Configuration
  # ==========================================================================
  iam_orchestrator = {
    role_ecs_name   = "${var.environment}-{{service_name}}-ecs-role"
    policy_ecs_name = "${var.environment}-{{service_name}}-ecs-policy"
    ecs_policy_actions = [
      # ECR (siempre necesario para pull de imagen)
      "ecr:GetAuthorizationToken",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      # CloudWatch Logs
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
      # Agregar según necesidad:
      # "secretsmanager:GetSecretValue",  # Si usa Secrets Manager
      # "s3:GetObject",                   # Si lee de S3
      # "s3:PutObject",                   # Si escribe a S3
      # "s3:ListBucket",                  # Si lista S3
      # "s3:DeleteObject",                # Si borra de S3
      # "ssm:GetParametersByPath",        # Si usa Parameter Store
      # "sns:Publish",                    # Si publica a SNS
      # "sqs:SendMessage",               # Si envía a SQS
      # "sqs:ReceiveMessage",            # Si lee de SQS
      # "sqs:DeleteMessage",             # Si borra de SQS
    ]
  }

  # ==========================================================================
  # ECR Configuration
  # ==========================================================================
  ecr_orchestrator = {
    name = "${var.environment}-{{service_name}}-repository"
  }

  # ==========================================================================
  # ECS Configuration
  # ==========================================================================
  ecs_cluster_configuration = {
    memory  = {{memory}}       # MB — 1024, 2048, 3072, 4096
    cpu     = "{{cpu}}"        # millicores — "256", "512", "1024", "2048"
    version = "v1.0.0"
  }

  # ==========================================================================
  # Target Group Configuration (solo para servicios web/API)
  # ==========================================================================
  target_group_configuration = {
    port              = "{{container_port}}"
    prefix_path       = "{{path_prefix}}"
    health_check_path = "{{path_prefix}}/actuator/health"  # Ajustar al framework
  }

  # ==========================================================================
  # CloudWatch Configuration
  # ==========================================================================
  cloudwatch_configuration = {
    log_group_name    = "ecs/${var.environment}/${var.project_name_snake_case}/${var.component_name_snake_case}"
    log_stream_name   = "log"
    retention_in_days = var.environment == "dev" ? 1 : 7
  }
}
```

## Variables a reemplazar

| Placeholder | Descripción | Ejemplo |
|------------|-------------|---------|
| `{{service_name}}` | Nombre del servicio en kebab-case | `project-name` |
| `{{memory}}` | Memoria en MB | `3072` |
| `{{cpu}}` | CPU en millicores (string) | `"2048"` |
| `{{container_port}}` | Puerto del contenedor | `"80"` |
| `{{path_prefix}}` | Prefijo del path de la API | `/api/documents/v2` |

## Guía de sizing

| Tipo de servicio | CPU | Memoria |
|-----------------|-----|---------|
| API pequeña (bajo tráfico) | 512 | 1024 |
| API mediana | 1024 | 2048 |
| API grande (alto tráfico) | 2048 | 3072-4096 |
| Worker/procesador | 1024-2048 | 2048-4096 |
| Tarea batch | 256-512 | 512-1024 |

## Health check paths comunes

| Framework | Health check path |
|-----------|------------------|
| Spring Boot | `/actuator/health` |
| NestJS | `/health` |
| Express | `/health` |
| FastAPI | `/health` |
| Django | `/health/` |
