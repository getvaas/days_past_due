---
description: >-
  Agregar un recurso de infraestructura a un proyecto de Vaas que ya tiene Terraform configurado.
  Usar cuando el developer dice "add s3 bucket", "agregar SQS", "necesito un nuevo recurso",
  "add a database", "agregar parameter store", "necesito SNS", "add secrets manager".
---

# vaas.infra.add — Agregar recurso a infraestructura existente

Agrega un recurso nuevo (S3, SQS, SNS, Parameter Store, Secrets Manager, Lambda, etc.) a un proyecto que ya tiene `deploy/terraform/` configurado.

## Restricciones

- **Operaciones permitidas** (read-only):
  - `terraform plan` (vía `make plan ENV=<env>`) — opcionalmente al final, para validar el recurso agregado antes de que el developer haga `make apply`.
  - `aws sso login` — solo cuando el developer lo elige explícitamente en el prompt de credenciales. Nunca se ejecuta de forma automática.
- **Operaciones prohibidas** (state-modifying):
  - `terraform apply`, `terraform destroy`, `terraform import`, `terraform state *`.
  - Cualquier comando que modifique recursos en AWS.
- **No auto-retry de credenciales**: si `make plan` falla por cualquier motivo, se informa el error textual al developer y se sugiere el comando manual. No se vuelve a intentar automáticamente.
- **Respeta las convenciones existentes** del proyecto — lee la infra actual antes de generar.
- **Usa los módulos de tf_modules** — nunca crea recursos directamente.
- **Actualiza** main.tf, inputs.tf, locals.tf según corresponda.

## Prompt de credenciales AWS (compartido con `vaas.infra.setup` y `vaas.infra.plan`)

Antes de ejecutar cualquier `make plan ENV=<env>`, la skill debe preguntar al developer cómo manejar las credenciales AWS. Nunca corre `aws sso login` sin que el developer lo elija explícitamente, y nunca reintenta automáticamente.

**Prompt exacto** (sustituir `<env>` y `<profile>` por los valores reales):

```
Para correr `make plan ENV=<env>` necesito credenciales AWS válidas.
  1) Ya tengo credenciales cargadas (env vars o `aws sso login` previo) — correr plan directo.
  2) Hacer `aws sso login --profile <profile>` ahora antes del plan.
  3) Cancelar — no correr plan.
```

**Acciones según la respuesta:**

- **Opción 1**: ejecutar `make plan ENV=<env>` directo. Si falla, informar error textual y sugerir comando manual. **No reintentar.**
- **Opción 2**: ejecutar `aws sso login --profile <profile>`. Si falla, informar error y no correr plan. Si OK, ejecutar `make plan ENV=<env>` y aplicar la misma lógica que la opción 1.
- **Opción 3**: no correr plan. Continuar el flujo sin output.

**Resolución del `<profile>`**: leer `deploy/terraform/configuration/<env>/profile.tfvars`, extraer línea no comentada `profile = "<X>"`. Si no existe o está comentada, usar `default`.

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
2. **Cómo verificar** — `make plan ENV=dev` (la skill puede ofrecer correrlo en el paso 7)
3. **Valores pendientes** — si hay placeholders `TODO_*`
4. **Permisos IAM actualizados** — qué acciones se agregaron y por qué

### Paso 7: Ofrecer correr `make plan` (opcional)

Después de generar los archivos, preguntar al developer si quiere validar con `make plan` antes de hacer `make apply` manualmente.

**Precondiciones para ofrecer plan:**

- No hay `TODO_*` pendientes en `deploy/terraform/configuration/`. Si hay, omitir este paso y sugerir completar los placeholders primero.
- El developer no canceló explícitamente la verificación.

**Si el developer acepta correr plan:**

1. Resolver el ambiente. Default: `dev`. Valores aceptados: `dev`, `stg`, `prod`.
2. Aplicar el **Prompt de credenciales AWS** (ver sección superior del archivo) con el `<env>` resuelto y el `<profile>` leído de `deploy/terraform/configuration/<env>/profile.tfvars`.
3. Mostrar el output del plan al developer (si hubo) o el error textual con sugerencias manuales (si falló).
4. No correr `make apply` — es siempre paso manual del developer.

## Ejemplos

Consultar `examples/` para ver casos concretos:
- `examples/example-add-s3.md` — Agregar bucket S3
- `examples/example-add-sqs.md` — Agregar cola SQS con SNS
- `examples/example-add-parameter-store.md` — Agregar Parameter Store
