---
description: >-
  Crear o configurar infraestructura Terraform para un proyecto de Vaas.
  Usar cuando el developer dice "setup infra", "create infrastructure",
  "configure terraform", "necesito crear la infra de mi proyecto",
  "inicializar terraform", "setup terraform".
---

# vaas.infra.setup — Crear infraestructura Terraform desde cero

Genera la estructura completa de Terraform para un proyecto de Vaas usando los módulos de `tf_modules`.
El developer no necesita conocer Terraform — esta skill genera todo el código y explica cómo usarlo.

## Restricciones

- **Solo genera archivos**. Nunca ejecuta `terraform plan` ni `terraform apply`.
- **Sigue el patrón de documents-api** como referencia de estructura.
- **Usa los módulos de tf_modules** — nunca crea recursos directamente.
- **Genera para los 3 ambientes**: dev, stg, prod.

## Referencias

Lee estos archivos antes de generar cualquier código:

- `references/modules-catalog.md` — Catálogo completo de los 15 módulos de tf_modules con inputs, ejemplos y comportamiento automático
- `references/environment-config.md` — Valores de AWS por ambiente (cuentas, VPCs, ALBs, clusters, subnets, SNS topics)
- `references/project-structure.md` — Estructura estándar de deploy/terraform/ con descripción de cada archivo
- `references/terraform-basics.md` — Conceptos mínimos de Terraform para explicar al developer

## Flujo de ejecución

### Paso 1: Detectar estado del proyecto

```
¿Existe deploy/terraform/ en el proyecto?
  → SÍ: Modo modificación — leer infra existente, preguntar qué cambiar
  → NO: Modo creación desde cero — seguir al Paso 2
```

Si el proyecto ya tiene infra, leer los archivos existentes y preguntar al developer qué necesita modificar. Considerar usar `vaas.infra.add` si solo necesita agregar un recurso.

### Paso 2: Recopilar información (modo creación)

Hacer las siguientes preguntas al developer. Si alguna respuesta no es clara, usar defaults sensatos.

1. **¿Qué tipo de servicio es?**
   - API / servicio web (→ `ecs_service`)
   - Worker / procesador de eventos (→ `ecs_service` sin routing público)
   - Tarea programada / cron job (→ `ecs_task`)
   - Lambda function (→ `lambda` + `iam_lambda`)

2. **¿Nombre del servicio?** (e.g., "notifications-api", "loan-processor")

3. **¿Qué recursos adicionales necesita?** (selección múltiple)
   - S3 bucket (almacenamiento de archivos)
   - SQS/SNS (cola de mensajes)
   - Parameter Store (configuración)
   - Secrets Manager (secretos)
   - Ninguno adicional

4. **Para APIs: ¿Path pattern para el ALB?** (e.g., `/api/notifications/*`)
   - Default: `/api/<service-name>/*`

5. **¿Puerto del contenedor?**
   - Default: `8080` para Java/Spring, `3000` para Node, `8000` para Python

### Paso 3: Generar la estructura

Consultar `references/modules-catalog.md` para seleccionar los módulos correctos y generar:

#### Archivos del root module:

1. **`deploy/terraform/main.tf`** — Orquestador
   - Usar `templates/main-tf.md` como base
   - Backend S3, provider AWS con default_tags
   - Importar módulos según lo que necesite el proyecto
   - Usar `git@github.com:getvaas/tf_modules.git//ecs_service` para el servicio principal

2. **`deploy/terraform/inputs.tf`** — Variables
   - Usar `templates/inputs-tf.md` como base
   - Incluir: environment, aws_region, vpc_id, subnets, naming, metadata, ALB ARNs, capacity_provider

3. **`deploy/terraform/locals.tf`** — Configuración computada
   - Usar `templates/locals-tf.md` como base
   - Definir config de IAM, ECR, ECS, CloudWatch, Target Group

4. **`deploy/terraform/configuration/`** — Ambientes
   - `global.tfvars` con valores compartidos
   - `dev/vars.tfvars`, `dev/backend.conf`, `dev/profile.tfvars`
   - `stg/vars.tfvars`, `stg/backend.conf`, `stg/profile.tfvars`
   - `prod/vars.tfvars`, `prod/backend.conf`, `prod/profile.tfvars`
   - Usar `references/environment-config.md` para los valores por ambiente

5. **Módulos locales** según el tipo de servicio:
   - `iam/iam_orchestrator.tf` — Roles y policies
   - `ecr/ecr_orchestrator.tf` — Repositorio de imágenes
   - `cloudwatch/cloudwatch_orchestrator.tf` — Log group
   - Otros según recursos adicionales: `s3/`, `sqs/`, `sns_sqs/`, `parameter_store/`

6. **`Makefile`** — Comandos de Terraform
   - Usar `templates/makefile.md` como base

### Paso 4: Explicar al developer

Después de generar los archivos, explicar brevemente:

1. **Qué se creó** — lista de archivos y su propósito (1 línea cada uno)
2. **Cómo ejecutar** — los comandos exactos:
   ```bash
   make plan ENV=dev      # Ver qué se va a crear
   make apply ENV=dev     # Crear los recursos
   ```
3. **Qué valores necesita obtener** — si hay placeholders como `TODO_*`, explicar de dónde obtener los valores reales (equipo de plataforma, Secrets Manager, etc.)
4. **Próximos pasos** — sugerir `vaas.infra.cicd` para CI/CD si aún no tiene Jenkinsfile

## Ejemplos

Consultar los archivos en `examples/` para ver implementaciones completas:
- `examples/example-ecs-service.md` — API Java/Spring con ECS service (como documents-api)
- `examples/example-lambda.md` — Lambda function con EventBridge schedule
- `examples/example-scheduled-task.md` — ECS task programada

## Templates

Los archivos en `templates/` son plantillas base para cada archivo generado:
- `templates/main-tf.md` — main.tf
- `templates/inputs-tf.md` — inputs.tf
- `templates/locals-tf.md` — locals.tf
- `templates/makefile.md` — Makefile
- `templates/backend-conf.md` — backend.conf
