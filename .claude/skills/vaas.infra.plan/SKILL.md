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
- **Operaciones permitidas** (read-only):
  - `terraform plan` (vía `make plan ENV=<env>`) — opcionalmente, si el developer quiere ver el diff real entre código y AWS.
  - `aws sso login` — solo cuando el developer lo elige explícitamente en el prompt de credenciales. Nunca se ejecuta de forma automática.
- **Operaciones prohibidas** (state-modifying):
  - `terraform apply`, `terraform destroy`, `terraform import`, `terraform state *`.
- **No auto-retry de credenciales**: si `make plan` falla por cualquier motivo, se informa el error textual al developer y se sugiere el comando manual. No se vuelve a intentar automáticamente.
- **Explica en lenguaje simple** — el developer puede no conocer Terraform.
- **Sugiere mejoras** basadas en las convenciones de Vaas y best practices.

## Prompt de credenciales AWS (compartido con `vaas.infra.setup` y `vaas.infra.add`)

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

### Paso 6: Ofrecer correr `make plan` (opcional)

Si el developer quiere ver el diff real entre el código Terraform y el estado actual en AWS, ofrecer correr `make plan ENV=<env>`.

**Si el developer acepta:**

1. Resolver el ambiente. Default: `dev`. Valores aceptados: `dev`, `stg`, `prod`.
2. Aplicar el **Prompt de credenciales AWS** (ver sección superior del archivo) con el `<env>` resuelto y el `<profile>` leído de `deploy/terraform/configuration/<env>/profile.tfvars`.
3. Mostrar el output del plan al developer (si hubo) o el error textual con sugerencias manuales (si falló).
4. Si el developer quiere inspeccionar otro ambiente después, repetir desde el paso 1 con el nuevo `<env>`.

**Comandos manuales (alternativa)** si el developer prefiere correrlos por su cuenta:

```bash
make plan ENV=dev      # Ver estado actual y cambios pendientes
make plan ENV=prod     # Verificar estado en producción
```
