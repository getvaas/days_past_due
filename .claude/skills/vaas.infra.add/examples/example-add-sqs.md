# Ejemplo: Agregar cola SQS con SNS a proyecto existente

## Contexto

El proyecto `documents-api` necesita una cola SQS para procesar eventos de documentos generados. Se crea con SNS topic, dead-letter queue, y alarmas CloudWatch.

## Archivos modificados

### 1. Crear `deploy/terraform/sns_sqs/` (módulo local nuevo)

Copiar el módulo completo de `common-recipes.md → SQS/SNS` (main.tf, input.tf, output.tf).

### 2. Agregar módulo en `deploy/terraform/main.tf`

```hcl
module "document_generated_queue" {
  source               = "./sns_sqs"
  name                 = replace("${local.name}-document-generated", "-", "_")
  visibility_timeout   = 1800
  max_receive_count    = 10
  message_retention_seconds = 86400
  environment          = var.environment
  sns_alarms_topic_arn = var.sns_alarms_topic_arn
}
```

Y pasar los ARNs al servicio ECS:
```hcl
module "ecs_service" {
  environment_variables = merge(var.environment_variables, {
    # ... variables existentes ...
    "DOCUMENT_GENERATED_TOPIC_ARN" = module.document_generated_queue.sns_topic_arn
    "DOCUMENT_GENERATED_QUEUE_URL" = module.document_generated_queue.sqs_execute_process_url
  })
}
```

### 3. Actualizar permisos IAM en `deploy/terraform/locals.tf`

Agregar a `ecs_policy_actions`:
```hcl
"sns:Publish",
"sqs:ReceiveMessage",
"sqs:DeleteMessage",
"sqs:GetQueueAttributes",
```

### Verificar

```bash
make plan ENV=dev
# Debería mostrar: Plan: ~7 to add (SNS topic, SQS queue, DLQ, subscription, policy, 2 alarms)
```
