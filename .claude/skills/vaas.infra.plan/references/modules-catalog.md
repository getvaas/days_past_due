# Vaas Terraform Modules Catalog

Source: `git@github.com:getvaas/tf_modules.git`

Este catálogo documenta los 15 módulos de Terraform disponibles en Vaas. Cada módulo se consume como:

```hcl
module "example" {
  source = "git@github.com:getvaas/tf_modules.git//module_name"
}
```

---

## ECS Service Modules

### ecs_service — Servicio ECS single-port (EL MÁS USADO)

**Source**: `git@github.com:getvaas/tf_modules.git//ecs_service`
**Propósito**: Servicio ECS con un puerto detrás de ALB (público + interno). Es el módulo más común para APIs y servicios web.

**Inputs requeridos**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `environment` | string | `dev`, `stg`, `prod` |
| `ecs_service_name` | string | Nombre del servicio, e.g. `"dev-documents-api"` |
| `ecs_cpu_millis_min` | number | CPU en millicores, e.g. `2048` |
| `ecs_memory_min` | number | Memoria en MB, e.g. `3072` |
| `sns_alarms_topic_arn` | string | ARN del topic de alarmas SNS |
| `lb_listener_rules` | list(object) | Reglas de routing del ALB (priority, conditions) |

**Inputs opcionales más usados**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `ecr_repository_uri` | string | `null` | URI del ECR. Si no se pasa, crea uno automáticamente |
| `ecr_repository_version_tag` | string | `"latest"` | Tag de la imagen Docker |
| `container_port` | number | `8080` | Puerto del contenedor |
| `host_port` | number | `0` | Debe ser 0 para dynamic port mapping |
| `environment_variables` | map(string) | `{}` | Variables de entorno del contenedor |
| `secrets` | map(string) | `{}` | Secretos desde Secrets Manager (formato `"ARN:key::"`) |
| `secrets_manager_arn` | string | `""` | ARN del secret en Secrets Manager |
| `secrets_manager_keys` | list(string) | `[]` | Keys a extraer del secret |
| `add_telemetry` | bool | `false` | Inyecta OTEL labels y env vars |
| `docker_labels` | map(string) | `null` | Labels Docker custom |
| `arm_service` | bool | `true` | ARM (true) vs x86 (false) |
| `enable_public_routing` | bool | `true` | Habilita routing público via ALB |
| `enable_internal_routing` | bool | `true` | Habilita routing interno via ALB |
| `lb_https_listener_arn` | string | `null` | ARN del listener HTTPS del ALB público (legacy, usar `lb_public_https_listener_arn`) |
| `lb_public_https_listener_arn` | string | `null` | ARN del listener HTTPS del ALB público |
| `lb_internal_https_listener_arn` | string | `null` | ARN del listener HTTPS del ALB interno |
| `lb_internal_listener_rules` | list(object) | `null` | Reglas del ALB interno (si difieren de las públicas) |
| `ecs_role_arn` | string | `null` | Rol IAM. Si no se pasa, crea uno automáticamente |
| `ecs_policy_actions` | list(string) | `[]` | Acciones IAM para el rol auto-creado |
| `ecs_policy_statements` | list(object) | `[]` | Statements IAM completos `{Effect, Action, Resource}` |
| `capacity_provider` | string | `null` | Capacity provider. Auto-resuelto si no se pasa |
| `cloudwatch_log_group_name` | string | `null` | Log group. Auto-creado si no se pasa |
| `health_check_path` | string | `"/actuator/health"` | Path del health check |
| `protocol` | string | `"HTTP"` | Protocolo del target group |
| `vpc_id` | string | `""` | VPC ID. Auto-resuelto si no se pasa |
| `scheduling_strategy` | string | `"REPLICA"` | `REPLICA` o `DAEMON` |
| `command` | list(string) | `null` | Override del CMD del contenedor |
| `entry_point` | list(string) | `null` | Override del ENTRYPOINT |
| `skip_destroy` | bool | `true` | Previene destrucción accidental |
| `mount_points` | list(object) | `null` | Mount points para EFS |
| `volumes` | list(object) | `[]` | Volúmenes (EFS) |
| `prefix_path` | string | `""` | Prefijo de path (deprecated) |

**Ejemplo mínimo**:
```hcl
module "my_service" {
  source               = "git@github.com:getvaas/tf_modules.git//ecs_service"
  environment          = var.environment
  ecs_service_name     = "${var.environment}-my-service"
  ecs_cpu_millis_min   = 512
  ecs_memory_min       = 1024
  sns_alarms_topic_arn = var.sns_alarms_topic_arn
  lb_listener_rules = [{
    priority    = 5000
    action_type = "forward"
    conditions  = [{ field = "path_pattern", values = ["/api/my-service/*"] }]
  }]
  enable_public_routing  = true
  enable_internal_routing = true
  capacity_provider      = var.capacity_provider
}
```

**Ejemplo completo** (como documents-api):
```hcl
module "ecs_service" {
  source                    = "git@github.com:getvaas/tf_modules.git//ecs_service"
  ecs_role_arn              = module.iam_orchestrator.ecs_role_arn
  ecs_memory_min            = 3072
  ecs_cpu_millis_min        = 2048
  ecr_repository_uri        = module.ecr_orchestrator.ecr_repository_uri
  ecs_service_name          = "${var.environment}-my-service"
  container_port            = 80
  environment               = var.environment
  health_check_path         = "/api/my-service/actuator/health"
  secrets = {
    "DB_HOST":     "${var.credentials_secret_manager}:host::",
    "DB_USERNAME": "${var.credentials_secret_manager}:username::",
    "DB_PASSWORD": "${var.credentials_secret_manager}:password::",
  }
  environment_variables = merge(var.environment_variables, {
    "AWS_REGION":             var.aws_region,
    "SPRING_PROFILES_ACTIVE": var.environment,
    "ENVIRONMENT":            var.environment,
  })
  add_telemetry             = true
  cloudwatch_log_group_name = "ecs/${var.environment}/my_project/my_service"
  sns_alarms_topic_arn      = var.sns_alarms_topic_arn
  capacity_provider         = var.capacity_provider
  lb_listener_rules = [{
    priority    = 2
    action_type = "forward"
    conditions  = [{ field = "path_pattern", values = ["/api/my-service/*"] }]
  }]
  enable_internal_routing = true
  enable_public_routing   = true
}
```

**Comportamiento automático**:
- Cluster: `<env>-one-cluster` (auto-resuelto por environment)
- Capacity provider: `<env>_arm_one_cluster_capacity_provider` (auto-resuelto)
- Log group: `/ecs/<service_name>` (auto-creado si no se pasa `cloudwatch_log_group_name`)
- ECR: `<service_name>-repository` (auto-creado si no se pasa `ecr_repository_uri`)
- IAM role: auto-creado si no se pasa `ecs_role_arn`
- Retention: 30d prod, 7d dev/stg
- Min healthy: 0% dev, 50% stg/prod

**Outputs**:
- `ecs_execution_role_arn` — ARN del rol de ejecución

---

### ecs_service_multiple_ports — Servicio ECS multi-puerto

**Source**: `git@github.com:getvaas/tf_modules.git//ecs_service_multiple_ports`
**Propósito**: Servicio ECS con múltiples puertos, cada uno con su propio target group y reglas de ALB.

**Inputs requeridos**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `environment` | string | `dev`, `stg`, `prod` |
| `ecs_service_name` | string | Nombre del servicio |
| `ecs_cpu_millis_min` | number | CPU en millicores |
| `ecs_memory_min` | number | Memoria en MB |
| `ecr_repository_uri` | string | URI del ECR (requerido, no auto-crea) |
| `sns_alarms_topic_arn` | string | ARN del topic de alarmas |
| `port_config` | list(object) | Configuración por puerto (ver abajo) |

**port_config** estructura:
```hcl
port_config = [
  {
    lb_target_group_name = "my-svc-http"    # max 32 chars
    container_port       = 8080
    tg_protocol          = "HTTP"
    health_check_path    = "/actuator/health"
    listener_rules = [{
      priority   = 100
      conditions = [{ field = "path_pattern", values = ["/api/*"] }]
    }]
  },
  {
    lb_target_group_name = "my-svc-grpc"
    container_port       = 9090
    tg_protocol          = "HTTP"
    tg_protocol_version  = "GRPC"
    health_check_path    = "/grpc.health.v1.Health/Check"
    listener_rules = [...]
  }
]
```

**Inputs opcionales**: Mismos que `ecs_service` excepto los específicos de single-port. Adicional:
- `sidecar_containers` (list(any), default=[]): Contenedores sidecar adicionales

---

### ecs_shared — Capa interna compartida

**Source**: `git@github.com:getvaas/tf_modules.git//ecs_shared`
**Propósito**: Módulo interno usado por `ecs_service` y `ecs_service_multiple_ports`. **No usar directamente**.

Resuelve: ECR auto-creation, IAM auto-creation, environment merging, telemetry labels, capacity provider defaults.

---

### ecs_task — Tarea ECS programada o one-off

**Source**: `git@github.com:getvaas/tf_modules.git//ecs_task`
**Propósito**: Task definition para tareas programadas (cron) o ejecuciones one-off. No es un servicio long-running.

**Inputs requeridos**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `environment` | string | `dev`, `stg`, `prod` |
| `aws_region` | string | e.g. `"us-east-1"` |
| `ecs_task_name` | string | Nombre de la tarea |

**Inputs opcionales más usados**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `ecs_cpu_millis_min` | number | `256` | CPU en millicores |
| `ecs_memory_min` | number | `512` | Memoria en MB |
| `ecr_repository_uri` | string | `null` | URI del ECR (auto-crea si null) |
| `ecr_repository_version_tag` | string | `"latest"` | Tag de imagen |
| `environment_variables` | map(string) | `{}` | Variables de entorno |
| `secrets` | map(string) | `{}` | Secretos |
| `schedule_expression` | string | `null` | Cron expression, e.g. `"cron(0 6 * * ? *)"` |
| `run_every_hours` | number | `6` | Alternativa simple a schedule_expression |
| `task_count` | number | `1` | Tareas paralelas |
| `enable_execute_command` | bool | `false` | ECS Exec (debug SSH) |
| `arm_service` | bool | `false` | ARM vs x86 (default x86 para tasks) |
| `ecs_network_mode` | string | `"bridge"` | `bridge` o `awsvpc` |
| `subnet_ids` | list(string) | `[]` | Subnets (necesario para awsvpc) |
| `security_group_ids` | list(string) | `[]` | Security groups (necesario para awsvpc) |
| `command` | list(string) | `null` | Override del CMD |
| `entry_point` | list(string) | `null` | Override del ENTRYPOINT |
| `mount_points` | any | `[]` | Mount points EFS |
| `volumes` | list(object) | `[]` | Volúmenes |
| `efs_id` | string | `""` | EFS filesystem ID |

**Ejemplo — tarea programada**:
```hcl
module "my_scheduled_task" {
  source              = "git@github.com:getvaas/tf_modules.git//ecs_task"
  environment         = var.environment
  aws_region          = var.aws_region
  ecs_task_name       = "${var.environment}-data-sync"
  ecs_cpu_millis_min  = 512
  ecs_memory_min      = 1024
  schedule_expression = "cron(0 2 * * ? *)"  # Todos los días a las 2 AM
  environment_variables = {
    "ENVIRONMENT" = var.environment
  }
}
```

---

## Container Registry

### ecr — Repositorio ECR

**Source**: `git@github.com:getvaas/tf_modules.git//ecr`
**Propósito**: Repositorio de imágenes Docker con scan-on-push.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `name` | string | (requerido) | Nombre del repositorio |
| `image_tag_mutability` | string | `"MUTABLE"` | `MUTABLE` o `IMMUTABLE` |

**Ejemplo**:
```hcl
module "ecr" {
  source = "git@github.com:getvaas/tf_modules.git//ecr"
  name   = "${var.environment}-my-service-repository"
}
```

**Outputs**:
- `ecr_repository_uri` — URI para push/pull de imágenes

---

## Logging

### cloudwatch — Log Group

**Source**: `git@github.com:getvaas/tf_modules.git//cloudwatch`
**Propósito**: CloudWatch log group con retention basada en environment.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `log_group_name` | string | (requerido) | Nombre del log group |
| `log_stream_name` | string | `null` | Nombre del log stream (opcional) |
| `retention_in_days` | string | `null` | Días de retención (auto si null) |
| `environment` | string | `null` | Para auto-resolver retention |

**Ejemplo**:
```hcl
module "cloudwatch" {
  source         = "git@github.com:getvaas/tf_modules.git//cloudwatch"
  log_group_name = "ecs/${var.environment}/my_project/my_service"
  environment    = var.environment
}
```

**Outputs**:
- `cloudwatch_log_group_name`
- `cloudwatch_log_group_arn`

---

## Load Balancing

### target_group_with_listeners_rules — Target Group + Listener Rules

**Source**: `git@github.com:getvaas/tf_modules.git//target_group_with_listeners_rules`
**Propósito**: Target group de ALB con reglas de listener declarativas. Normalmente no se usa directamente — `ecs_service` lo usa internamente.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `lb_target_group_name` | string | (requerido) | Max 32 chars (límite AWS) |
| `listener_rules` | list(object) | (requerido) | Reglas con priority, conditions, listener_arn |
| `container_port` | number | `8080` | Puerto del contenedor |
| `tg_protocol` | string | `"HTTP"` | `HTTP` o `HTTPS` |
| `tg_protocol_version` | string | `"HTTP1"` | `HTTP1`, `HTTP2`, `GRPC` |
| `health_check_enabled` | bool | `true` | Habilitar health check |
| `health_check_path` | string | `"/actuator/health"` | Path del health check |
| `health_check_port` | string | `"traffic-port"` | Puerto del health check |
| `environment` | string | (requerido) | Para resolver VPC |

**Outputs**:
- `target_group_arn`

---

## IAM

### iam_ecs — Rol IAM para ECS

**Source**: `git@github.com:getvaas/tf_modules.git//iam_ecs`
**Propósito**: Rol IAM con trust policy para ECS tasks/services.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `ecs_role_name` | string | (requerido) | Nombre del rol |
| `ecs_policy_name` | string | (requerido) | Nombre de la policy |
| `ecs_policy_actions` | list(string) | `[]` | Acciones IAM simples (Resource: *) |
| `ecs_policy_statements` | list(object) | `[]` | Statements completos `{Effect, Action, Resource}` |

**Ejemplo**:
```hcl
module "iam_ecs" {
  source          = "git@github.com:getvaas/tf_modules.git//iam_ecs"
  ecs_role_name   = "${var.environment}-my-service-ecs-role"
  ecs_policy_name = "${var.environment}-my-service-ecs-policy"
  ecs_policy_actions = [
    "ecr:GetAuthorizationToken",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "secretsmanager:GetSecretValue",
    "s3:GetObject",
    "s3:PutObject",
    "ssm:GetParametersByPath",
    "sns:Publish"
  ]
}
```

**Outputs**:
- `ecs_role_arn` — ARN del rol
- `ecs_role_arn_name` — Nombre del rol

---

### iam_lambda — Rol IAM para Lambda

**Source**: `git@github.com:getvaas/tf_modules.git//iam_lambda`
**Propósito**: Rol IAM con trust policy para Lambda functions.

**Inputs**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `iam_configuration` | object | `{ role_lambda_name, policy_lambda_name, policy_lambda_actions }` |

**Ejemplo**:
```hcl
module "iam_lambda" {
  source = "git@github.com:getvaas/tf_modules.git//iam_lambda"
  iam_configuration = {
    role_lambda_name         = "${var.environment}-my-lambda-role"
    policy_lambda_name       = "${var.environment}-my-lambda-policy"
    policy_lambda_actions    = ["s3:GetObject", "s3:PutObject", "logs:*"]
  }
}
```

**Outputs**:
- `iam_role_lambda_arn`
- `iam_role_lambda_name`

---

### iam — Rol IAM genérico

**Source**: `git@github.com:getvaas/tf_modules.git//iam`
**Propósito**: Rol IAM genérico con policy statements custom.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `name` | string | (requerido) | Nombre del rol |
| `policy_statements` | list(object) | `[]` | Statements `{Effect, Action, Resource}` |

**Outputs**:
- `ecs_role_arn`
- `ecs_role_arn_name`

---

## Serverless

### lambda — Lambda Function

**Source**: `git@github.com:getvaas/tf_modules.git//lambda`
**Propósito**: AWS Lambda function con código desde S3.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `name` | string | (requerido) | Nombre de la función |
| `handler` | string | (requerido) | Handler, e.g. `"index.handler"` |
| `runtime` | string | `"python3.11"` | Runtime |
| `memory_size` | number | `256` | Memoria en MB |
| `timeout` | number | `60` | Timeout en segundos |
| `architectures` | list(string) | `[]` | `["x86_64"]` o `["arm64"]` |
| `layers` | list(string) | `[]` | ARNs de Lambda layers |
| `iam_role_lambda_arn` | string | (requerido) | ARN del rol de ejecución |
| `environment_variables` | map(any) | (requerido) | Variables de entorno |
| `s3_code_bucket` | string | (requerido) | Bucket S3 con el código |
| `s3_code_key` | string | (requerido) | Key del archivo en S3 |

**Ejemplo**:
```hcl
module "my_lambda" {
  source               = "git@github.com:getvaas/tf_modules.git//lambda"
  name                 = "${var.environment}-process-data"
  handler              = "index.handler"
  runtime              = "python3.11"
  memory_size          = 512
  timeout              = 300
  iam_role_lambda_arn  = module.iam_lambda.iam_role_lambda_arn
  s3_code_bucket       = "my-lambda-code-bucket"
  s3_code_key          = "process-data/latest.zip"
  environment_variables = {
    "ENVIRONMENT" = var.environment
    "TABLE_NAME"  = "my-table"
  }
}
```

**Outputs**:
- `lambda_function_arn`
- `lambda_function_name`

---

### eventbridge_invoke_lambda — EventBridge Schedule → Lambda

**Source**: `git@github.com:getvaas/tf_modules.git//eventbridge_invoke_lambda`
**Propósito**: Regla de EventBridge que invoca una Lambda en un schedule (cron).

**Inputs**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `name` | string | Nombre de la regla |
| `lambda_arn` | string | ARN de la Lambda |
| `lambda_name` | string | Nombre de la Lambda |
| `schedule_expression` | string | Cron expression, e.g. `"cron(0 12 * * ? *)"` |

**Ejemplo**:
```hcl
module "daily_trigger" {
  source              = "git@github.com:getvaas/tf_modules.git//eventbridge_invoke_lambda"
  name                = "${var.environment}-daily-process"
  lambda_arn          = module.my_lambda.lambda_function_arn
  lambda_name         = module.my_lambda.lambda_function_name
  schedule_expression = "cron(0 6 * * ? *)"
}
```

---

## Storage

### s3 — Bucket S3

**Source**: `git@github.com:getvaas/tf_modules.git//s3`
**Propósito**: Bucket S3 con defaults seguros (public access bloqueado).

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `bucket_name` | string | (requerido) | Nombre del bucket |
| `environment` | string | (requerido) | Para naming |
| `account_id` | string | `""` | Account ID (opcional) |

**Ejemplo**:
```hcl
module "s3" {
  source      = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name = "my-service-data"
  environment = var.environment
}
```

**Outputs**:
- `bucket_name` — Nombre completo del bucket
- `bucket_arn` — ARN del bucket

---

### parameter_store — AWS SSM Parameter Store

**Source**: `git@github.com:getvaas/tf_modules.git//parameter_store`
**Propósito**: Parámetros en AWS Systems Manager Parameter Store (tipo String).

**Inputs**:
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `prefix` | string | Prefijo del nombre del parámetro |
| `parameter_store_configuration` | map(any) | Mapa de parámetros `{ key = value }` |

**Ejemplo**:
```hcl
module "parameter_store" {
  source = "git@github.com:getvaas/tf_modules.git//parameter_store"
  prefix = "/${var.environment}/my-service"
  parameter_store_configuration = {
    "api_url"     = "https://api.example.com"
    "max_retries" = "3"
    "timeout_ms"  = "5000"
  }
}
```

**Outputs**:
- `parameter_store_environment` — Mapa de parámetros creados

---

## Messaging

### sns_sqs — SNS Topic + SQS Queue

**Source**: `git@github.com:getvaas/tf_modules.git//sns_sqs`
**Propósito**: Topic SNS conectado a cola SQS con dead-letter queue y alarmas CloudWatch.

**Inputs**:
| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `sqs_configuration` | object | (requerido) | Ver estructura abajo |
| `sns_publisher_iam_role` | string | (requerido) | ARN del rol que publica en SNS |

**sqs_configuration** estructura:
```hcl
sqs_configuration = {
  name                      = "my_queue"
  visibility_timeout        = 300        # Segundos
  message_retention_seconds = 86400      # 24 horas
  max_message_size          = 1024       # Bytes
  max_receive_count         = 3          # Reintentos antes de DLQ
}
```

**Ejemplo**:
```hcl
module "events_queue" {
  source = "git@github.com:getvaas/tf_modules.git//sns_sqs"
  sqs_configuration = {
    name                      = "${var.environment}_my_service_events"
    visibility_timeout        = 300
    message_retention_seconds = 86400
    max_message_size          = 2048
    max_receive_count         = 5
  }
  sns_publisher_iam_role = module.iam_ecs.ecs_role_arn
}
```

**Outputs**:
- `loan_tape_upload_sns_topic_name` — Nombre del topic SNS
- `loan_tape_upload_sns_topic_arn` — ARN del topic SNS
- `loan_tape_upload_queue_name` — Nombre de la cola SQS
- `loan_tape_upload_queue_arn` — ARN de la cola SQS

**Nota**: Los nombres de los outputs tienen un naming legacy (`loan_tape_upload_*`). Usar los valores, ignorar los nombres.

---

## Cuándo usar cada módulo

| Necesito... | Módulo |
|-------------|--------|
| API/servicio web con un puerto | `ecs_service` |
| Servicio con múltiples puertos (HTTP + gRPC) | `ecs_service_multiple_ports` |
| Tarea programada (cron) o batch | `ecs_task` |
| Función serverless | `lambda` + `iam_lambda` |
| Cron que invoca Lambda | `eventbridge_invoke_lambda` |
| Repositorio de imágenes Docker | `ecr` |
| Almacenamiento de archivos | `s3` |
| Cola de mensajes | `sns_sqs` |
| Configuración de la aplicación | `parameter_store` |
| Logs | `cloudwatch` |
| Rol IAM para ECS | `iam_ecs` (o el auto-creado de `ecs_service`) |
| Rol IAM para Lambda | `iam_lambda` |
| Rol IAM genérico | `iam` |
| Target group custom | `target_group_with_listeners_rules` |
