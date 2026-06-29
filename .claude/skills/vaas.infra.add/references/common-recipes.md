# Recetas para Agregar Recursos

Cada receta describe los pasos exactos para agregar un tipo de recurso a infraestructura existente.

---

## S3 — Bucket de almacenamiento

### Opción A: Usar módulo de tf_modules (recomendado para buckets simples)

```hcl
# En main.tf — agregar:
module "s3_{{bucket_purpose}}" {
  source      = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name = "{{bucket_purpose}}"
  environment = var.environment
}
```

### Opción B: Módulo local (si necesitas CORS, lifecycle rules, etc.)

Crear `deploy/terraform/s3/`:

**s3/main.tf**:
```hcl
resource "aws_s3_bucket" "bucket" {
  bucket = "${var.bucket_prefix}-${var.environment}-${var.bucket_name}"
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket                  = aws_s3_bucket.bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.bucket.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_ownership_controls" "ownership" {
  bucket = aws_s3_bucket.bucket.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_cors_configuration" "cors" {
  bucket = aws_s3_bucket.bucket.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["Access-Control-Allow-Origin"]
    max_age_seconds = 3000
  }
}
```

**s3/input.tf**:
```hcl
variable "bucket_name" {}
variable "bucket_prefix" {}
variable "environment" {}
```

**s3/output.tf**:
```hcl
output "bucket_name" { value = aws_s3_bucket.bucket.bucket }
output "bucket_arn" { value = aws_s3_bucket.bucket.arn }
```

### Permisos IAM a agregar en locals.tf:
```
"s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject"
```

---

## SQS/SNS — Cola de mensajes con topic

### Opción A: Módulo local con SNS + SQS + DLQ + alarmas (recomendado)

Crear `deploy/terraform/sns_sqs/`:

**sns_sqs/main.tf**:
```hcl
resource "aws_sns_topic" "sns_topic" {
  name         = "${var.name}_sns_topic"
  display_name = "${var.name}_sns_topic"
}

resource "aws_sqs_queue" "dead_letter_queue" {
  count                     = var.avoid_dl_queue ? 0 : 1
  name                      = "${var.name}_standard_dead_letter_queue"
  max_message_size          = var.max_message_size
  message_retention_seconds = var.message_retention_seconds
}

resource "aws_sqs_queue" "queue" {
  name                       = "${var.name}_standard_queue"
  max_message_size           = var.max_message_size
  message_retention_seconds  = var.message_retention_seconds
  visibility_timeout_seconds = var.visibility_timeout
}

resource "aws_sqs_queue_redrive_policy" "redrive" {
  count     = var.avoid_dl_queue ? 0 : 1
  queue_url = aws_sqs_queue.queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter_queue[0].arn
    maxReceiveCount     = var.max_receive_count
  })
}

resource "aws_sns_topic_subscription" "subscription" {
  endpoint             = aws_sqs_queue.queue.arn
  protocol             = "sqs"
  topic_arn            = aws_sns_topic.sns_topic.arn
  raw_message_delivery = true
}

resource "aws_sqs_queue_policy" "policy" {
  queue_url = aws_sqs_queue.queue.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNS"
      Effect    = "Allow"
      Principal = "*"
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.queue.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.sns_topic.arn } }
    }]
  })
}

# Alarmas
resource "aws_cloudwatch_metric_alarm" "queue_alarm" {
  alarm_name          = "${aws_sqs_queue.queue.name}_avg_age_old_msg"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Average"
  threshold           = 60 + aws_sqs_queue.queue.message_retention_seconds
  alarm_actions       = [var.sns_alarms_topic_arn]
  dimensions          = { QueueName = aws_sqs_queue.queue.name }
}

resource "aws_cloudwatch_metric_alarm" "dlq_alarm" {
  count               = var.avoid_dl_queue ? 0 : 1
  alarm_name          = "${aws_sqs_queue.dead_letter_queue[0].name}_dl_avg_age_old_msg"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 120
  statistic           = "Average"
  threshold           = 86400
  alarm_actions       = [var.sns_alarms_topic_arn]
  dimensions          = { QueueName = aws_sqs_queue.dead_letter_queue[0].name }
}
```

**sns_sqs/input.tf**:
```hcl
variable "visibility_timeout" { type = number }
variable "name" { type = string }
variable "message_retention_seconds" { type = number; default = 86400 }
variable "max_message_size" { type = number; default = 1024 }
variable "max_receive_count" { type = number; default = 3 }
variable "sns_publisher_iam_role" { type = string; default = "" }
variable "avoid_dl_queue" { type = bool; default = false }
variable "environment" { type = string }
variable "sns_alarms_topic_arn" { type = string }
```

**sns_sqs/output.tf**:
```hcl
output "sns_topic_name" { value = aws_sns_topic.sns_topic.name }
output "sns_topic_arn" { value = aws_sns_topic.sns_topic.arn }
output "queue_name" { value = aws_sqs_queue.queue.name }
output "queue_arn" { value = aws_sqs_queue.queue.arn }
output "sqs_execute_process_url" { value = aws_sqs_queue.queue.url }
```

### En main.tf agregar:
```hcl
module "{{queue_name}}_queue" {
  source               = "git@github.com:getvaas/tf_modules.git//sns_sqs"
  name                 = replace("${local.name}-{{queue_purpose}}", "-", "_")
  visibility_timeout   = 300
  max_receive_count    = 5
  message_retention_seconds = 86400
  environment          = var.environment
  sns_alarms_topic_arn = var.sns_alarms_topic_arn
}
```

### Permisos IAM:
```
"sns:Publish", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"
```

---

## Parameter Store — Configuración de aplicación

### Usar directamente tf_modules:

```hcl
# En main.tf:
module "parameter_store" {
  source = "git@github.com:getvaas/tf_modules.git//parameter_store"
  prefix = "/${var.environment}/{{service_name}}"
  parameter_store_configuration = {
    "key1" = "value1"
    "key2" = "value2"
  }
}
```

### Permisos IAM:
```
"ssm:GetParametersByPath", "ssm:GetParameter"
```

---

## Secrets Manager — Secretos de la aplicación

Secrets Manager no se crea desde Terraform usualmente — los secretos se crean manualmente en AWS Console o via CLI. Lo que se hace es **leer** el secreto como data source y pasarlo al contenedor.

### Agregar data source en main.tf:
```hcl
data "aws_secretsmanager_secret" "{{secret_name}}" {
  arn = var.{{secret_name}}_secret_manager
}
```

### Agregar variable en inputs.tf:
```hcl
variable "{{secret_name}}_secret_manager" {
  type        = string
  description = "ARN of the {{secret_name}} secret in Secrets Manager"
}
```

### Pasar como secret al módulo ECS en main.tf:
```hcl
module "ecs_service" {
  # ... inputs existentes ...
  secrets = {
    # Secrets existentes...
    "NEW_SECRET_KEY" = "${var.{{secret_name}}_secret_manager}:key_in_secret::"
  }
}
```

### Agregar ARN en vars.tfvars de cada ambiente:
```hcl
{{secret_name}}_secret_manager = "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:ENV-secret-name-XXXXXX"
```

### Permisos IAM:
```
"secretsmanager:GetSecretValue"
```

---

## Lambda — Función serverless

### Agregar en main.tf:
```hcl
module "iam_{{lambda_name}}" {
  source = "git@github.com:getvaas/tf_modules.git//iam_lambda"
  iam_configuration = {
    role_lambda_name      = "${var.environment}-{{lambda_name}}-role"
    policy_lambda_name    = "${var.environment}-{{lambda_name}}-policy"
    policy_lambda_actions = ["logs:*", "s3:GetObject"]
  }
}

module "{{lambda_name}}" {
  source              = "git@github.com:getvaas/tf_modules.git//lambda"
  name                = "${var.environment}-{{lambda_name}}"
  handler             = "index.handler"
  runtime             = "python3.11"
  memory_size         = 256
  timeout             = 60
  iam_role_lambda_arn = module.iam_{{lambda_name}}.iam_role_lambda_arn
  s3_code_bucket      = var.lambda_code_bucket
  s3_code_key         = "{{lambda_name}}/latest.zip"
  environment_variables = {
    "ENVIRONMENT" = var.environment
  }
}
```

---

## EventBridge — Trigger programado para Lambda

### Agregar en main.tf (después de definir la Lambda):
```hcl
module "{{trigger_name}}" {
  source              = "git@github.com:getvaas/tf_modules.git//eventbridge_invoke_lambda"
  name                = "${var.environment}-{{trigger_name}}"
  lambda_arn          = module.{{lambda_name}}.lambda_function_arn
  lambda_name         = module.{{lambda_name}}.lambda_function_name
  schedule_expression = "cron({{cron_expression}})"
}
```

### Ejemplos de cron:
- `cron(0 2 * * ? *)` — todos los días a las 2 AM
- `cron(0 */6 * * ? *)` — cada 6 horas
- `cron(0 0 ? * MON-FRI *)` — de lunes a viernes a medianoche
- `rate(5 minutes)` — cada 5 minutos

---

## CloudWatch — Log group adicional

```hcl
module "cloudwatch_{{purpose}}" {
  source         = "git@github.com:getvaas/tf_modules.git//cloudwatch"
  log_group_name = "ecs/${var.environment}/{{project}}/{{purpose}}"
  environment    = var.environment
}
```

---

## ECR — Repositorio de imágenes adicional

```hcl
module "ecr_{{purpose}}" {
  source = "git@github.com:getvaas/tf_modules.git//ecr"
  name   = "${var.environment}-{{purpose}}-repository"
}
```
