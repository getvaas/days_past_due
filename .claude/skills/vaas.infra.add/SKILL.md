---
description: >-
  Agregar un recurso de infraestructura a un proyecto de Vaas que ya tiene Terraform configurado.
  Usar cuando el developer dice "add s3 bucket", "agregar SQS", "necesito un nuevo recurso",
  "add a database", "agregar parameter store", "necesito SNS", "add secrets manager".
---

# vaas.infra.add — Agregar recurso a infraestructura existente

Agrega un recurso nuevo (S3, SQS, SNS, Parameter Store, Secrets Manager, Lambda, etc.) a un proyecto que ya tiene `deploy/terraform/` configurado.

## Restricciones

- **Solo genera archivos**. Nunca ejecuta `terraform plan` ni `terraform apply`.
- **Respeta las convenciones existentes** del proyecto — lee la infra actual antes de generar.
- **Usa los módulos de tf_modules** — nunca crea recursos directamente.
- **Actualiza** main.tf, inputs.tf, locals.tf según corresponda.

## Referencias

Lee estos archivos antes de generar cualquier código:

- `references/modules-catalog.md` — Catálogo completo de los 15 módulos de tf_modules
- `references/environment-config.md` — Valores de AWS por ambiente
- `references/common-recipes.md` — Recetas paso a paso para agregar cada tipo de recurso

## Flujo de ejecución

### Paso 1: Verificar que existe infraestructura

```
¿Existe deploy/terraform/?
  → NO: Informar al developer que use `vaas.infra.setup` primero
  → SÍ: Continuar
```

### Paso 2: Leer infraestructura actual

Leer los siguientes archivos del proyecto:
1. `deploy/terraform/main.tf` — entender qué módulos ya existen
2. `deploy/terraform/inputs.tf` — entender qué variables ya están definidas
3. `deploy/terraform/locals.tf` — entender la configuración existente
4. `deploy/terraform/configuration/global.tfvars` — valores globales
5. `deploy/terraform/configuration/dev/vars.tfvars` — al menos un ambiente para context

### Paso 3: Identificar qué recurso agregar

El developer puede pedir en lenguaje natural. Mapear a módulos:

| El developer pide... | Módulo a usar | Referencia |
|----------------------|--------------|------------|
| S3, bucket, almacenamiento de archivos | `s3` (tf_modules o local) | common-recipes.md → S3 |
| SQS, cola, queue, mensajes | `sns_sqs` (local) | common-recipes.md → SQS/SNS |
| SNS, topic, notificaciones, eventos | `sns_sqs` (local) | common-recipes.md → SQS/SNS |
| Parameter Store, configuración, SSM | `parameter_store` (tf_modules) | common-recipes.md → Parameter Store |
| Secrets Manager, secretos, credenciales | Data source + variable | common-recipes.md → Secrets Manager |
| Lambda, función serverless | `lambda` + `iam_lambda` (tf_modules) | common-recipes.md → Lambda |
| EventBridge, cron, schedule | `eventbridge_invoke_lambda` (tf_modules) | common-recipes.md → EventBridge |
| CloudWatch, logs | `cloudwatch` (tf_modules) | common-recipes.md → CloudWatch |
| ECR, repositorio de imágenes | `ecr` (tf_modules) | common-recipes.md → ECR |
| IAM, permisos, rol | `iam_ecs` o `iam` (tf_modules) | common-recipes.md → IAM |

### Paso 4: Generar los archivos

Seguir la receta correspondiente en `references/common-recipes.md`. Generalmente implica:

1. **Crear módulo local** (si aplica): `deploy/terraform/<recurso>/main.tf`, `input.tf`, `output.tf`
2. **Actualizar `main.tf`**: Agregar el nuevo módulo con sus inputs
3. **Actualizar `inputs.tf`**: Agregar nuevas variables si se necesitan
4. **Actualizar `locals.tf`**: Agregar configuración local si se necesita
5. **Actualizar `vars.tfvars`**: Agregar valores por ambiente para las nuevas variables

### Paso 5: Actualizar permisos IAM

Si el servicio ECS necesita acceso al nuevo recurso, actualizar los `ecs_policy_actions` en `locals.tf`:

| Recurso | Acciones IAM necesarias |
|---------|------------------------|
| S3 (lectura) | `s3:GetObject`, `s3:ListBucket` |
| S3 (escritura) | `s3:PutObject`, `s3:DeleteObject` |
| SQS (consumir) | `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` |
| SQS (publicar) | `sqs:SendMessage` |
| SNS (publicar) | `sns:Publish` |
| Parameter Store | `ssm:GetParametersByPath`, `ssm:GetParameter` |
| Secrets Manager | `secretsmanager:GetSecretValue` |

### Paso 6: Explicar al developer

1. **Qué archivos se crearon/modificaron** — lista con 1 línea por archivo
2. **Cómo verificar** — `make plan ENV=dev`
3. **Valores pendientes** — si hay placeholders `TODO_*`
4. **Permisos IAM actualizados** — qué acciones se agregaron y por qué

## Ejemplos

Consultar `examples/` para ver casos concretos:
- `examples/example-add-s3.md` — Agregar bucket S3
- `examples/example-add-sqs.md` — Agregar cola SQS con SNS
- `examples/example-add-parameter-store.md` — Agregar Parameter Store
