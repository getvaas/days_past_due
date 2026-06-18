---
description: >-
  Analizar y explicar la infraestructura Terraform existente de un proyecto de Vaas sin modificar archivos.
  Usar cuando el developer dice "analyze infra", "review terraform", "what infrastructure do I have",
  "plan infra changes", "explicar infra", "qué tengo configurado", "review my terraform",
  "qué es un target group", "por qué tenemos dos ALBs".
---

# vaas.infra.plan — Analizar infraestructura (read-only)

Analiza y explica la infraestructura Terraform existente de un proyecto de Vaas. No modifica ningún archivo — modo lectura y análisis solamente.

## Restricciones

- **NUNCA modifica archivos**. Solo lee y explica.
- **Explica en lenguaje simple** — el developer puede no conocer Terraform.
- **Sugiere mejoras** basadas en las convenciones de Vaas y best practices.

## Referencias

- `references/modules-catalog.md` — Catálogo de tf_modules para identificar qué módulos usa el proyecto
- `references/environment-config.md` — Valores de referencia para validar configuración

## Flujo de ejecución

### Paso 1: Verificar que existe infraestructura

```
¿Existe deploy/terraform/?
  → NO: Informar al developer y sugerir `vaas.infra.setup`
  → SÍ: Continuar
```

### Paso 2: Leer toda la infraestructura

Leer los siguientes archivos:
1. `deploy/terraform/main.tf` — módulos y orquestación
2. `deploy/terraform/inputs.tf` — variables de entrada
3. `deploy/terraform/locals.tf` — configuración computada
4. `deploy/terraform/configuration/global.tfvars` — valores globales
5. `deploy/terraform/configuration/dev/vars.tfvars` — valores de dev
6. Cualquier módulo local en subdirectorios (iam/, ecr/, s3/, sqs/, etc.)

### Paso 3: Generar inventario

Crear un inventario claro de todos los recursos:

```
## Infraestructura de [nombre-del-proyecto]

### Servicios
- ECS Service: [nombre] — [CPU]mb CPU, [memoria]MB RAM, puerto [puerto]
  - Routing: [path pattern] → ALB público + interno
  - Health check: [path]

### Storage
- S3: [bucket name] — [propósito]

### Messaging
- SQS: [queue name] — visibility timeout [N]s, DLQ: sí/no

### Secrets
- Secrets Manager: [N] secretos configurados
  - [lista de keys]

### IAM
- Rol ECS: [nombre] — [N] acciones permitidas
  - [lista resumida de permisos]

### Configuración por ambiente
| Variable | Dev | Stg | Prod |
|----------|-----|-----|------|
| CPU      | ... | ... | ...  |
| Memoria  | ... | ... | ...  |
```

### Paso 4: Responder preguntas

Si el developer tiene una pregunta específica, responderla usando:
- El contexto de la infraestructura del proyecto
- `references/modules-catalog.md` para explicar cómo funcionan los módulos
- `references/environment-config.md` para explicar los valores por ambiente
- Lenguaje simple, sin asumir conocimiento de Terraform

**Preguntas comunes**:
- "¿Qué es un target group?" → Explicar con analogía
- "¿Por qué tenemos dos ALBs?" → Público (internet) vs interno (entre servicios)
- "¿Qué permisos tiene el servicio?" → Listar las acciones IAM
- "¿Cómo se despliega?" → Explicar el flujo de ECS + ECR
- "¿Qué pasa si el servicio se cae?" → Health checks, min healthy percent, alarmas

### Paso 5: Sugerir mejoras (opcional)

Si se detectan oportunidades de mejora, sugerirlas:

| Detección | Sugerencia |
|-----------|-----------|
| No tiene `add_telemetry = true` | Habilitar telemetría OTEL |
| No tiene CloudWatch alarms | Agregar alarmas vía `sns_alarms_topic_arn` |
| Permisos IAM con `Resource = "*"` excesivos | Restringir a recursos específicos |
| No tiene DLQ en SQS | Agregar dead-letter queue |
| Log retention > 7 días en dev | Reducir para ahorrar costos |
| No usa ARM (`arm_service = false`) | Migrar a ARM para menor costo |
| Secrets hardcodeados en vars.tfvars | Mover a Secrets Manager |

### Paso 6: Comandos útiles

Si el developer necesita ejecutar algo, dar los comandos exactos:

```bash
make plan ENV=dev      # Ver estado actual y cambios pendientes
make plan ENV=prod     # Verificar estado en producción
```
