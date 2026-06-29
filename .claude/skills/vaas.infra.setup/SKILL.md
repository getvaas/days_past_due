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

- **Operaciones permitidas** (read-only):
  - `terraform plan` (vía `make plan ENV=<env>`) — en dos puntos del flujo:
    - **Modo modificación**: al inicio, para inspeccionar el estado actual antes de proponer cambios.
    - **Modo creación**: al final, para validar la estructura generada y dejarla lista para que el developer ejecute `make apply` manualmente.
  - `aws sso login` — solo cuando el developer lo elige explícitamente en el prompt de credenciales (ver "Prompt de credenciales AWS"). Nunca se ejecuta de forma automática.
- **Operaciones prohibidas** (state-modifying):
  - `terraform apply`, `terraform destroy`, `terraform import`, `terraform state *`.
  - Cualquier comando que modifique recursos en AWS.
- **No auto-retry de credenciales**: si `make plan` falla por cualquier motivo (incluido auth), se informa el error textual al developer y se sugiere el comando manual. No se vuelve a intentar automáticamente.
- **Sigue el patrón estándar de Vaas** como referencia de estructura.
- **Usa los módulos de tf_modules** — nunca crea recursos directamente.
- **Genera para los 3 ambientes**: dev, stg, prod.

## Referencias

Lee estos archivos antes de generar cualquier código:

- `references/modules-catalog.md` — Catálogo completo de los 15 módulos de tf_modules con inputs, ejemplos y comportamiento automático
- `references/environment-config.md` — Valores de AWS por ambiente (cuentas, VPCs, ALBs, clusters, subnets, SNS topics)
- `references/project-structure.md` — Estructura estándar de deploy/terraform/ con descripción de cada archivo
- `references/terraform-basics.md` — Conceptos mínimos de Terraform para explicar al developer

## Prompt de credenciales AWS (compartido entre todos los flujos que corren `make plan`)

Antes de ejecutar cualquier `make plan ENV=<env>`, la skill debe preguntar al developer cómo manejar las credenciales AWS. Nunca corre `aws sso login` sin que el developer lo elija explícitamente, y nunca reintenta automáticamente.

**Prompt exacto** (sustituir `<env>` y `<profile>` por los valores reales):

```
Para correr `make plan ENV=<env>` necesito credenciales AWS válidas.
  1) Ya tengo credenciales cargadas (env vars o `aws sso login` previo) — correr plan directo.
  2) Hacer `aws sso login --profile <profile>` ahora antes del plan.
  3) Cancelar — no correr plan.
```

**Acciones según la respuesta:**

- **Opción 1**: ejecutar `make plan ENV=<env>` directo.
  - Si exit code = 0 → mostrar output al developer.
  - Si exit code ≠ 0 → informar el error textual exacto al developer, sugerir comandos manuales (`aws sso login --profile <X>`, verificar `~/.aws/config`, etc.) y continuar el flujo sin output de plan. **No reintentar.**
- **Opción 2**: ejecutar `aws sso login --profile <profile>`.
  - Si `sso login` falla → informar error y sugerir comandos manuales. **No correr plan.** Continuar el flujo sin output de plan.
  - Si `sso login` se completa → ejecutar `make plan ENV=<env>`.
    - Si exit code = 0 → mostrar output.
    - Si exit code ≠ 0 → informar error textual y sugerir comandos manuales. **No reintentar.**
- **Opción 3**: no correr plan. Continuar el flujo sin output de plan.

**Resolución del `<profile>`**: leer `deploy/terraform/configuration/<env>/profile.tfvars`, extraer línea no comentada `profile = "<X>"`. Si el archivo no existe, la línea está comentada, o la asignación está ausente → usar `default`.

## Flujo de ejecución

### Paso 1: Detectar estado del proyecto

```
¿Existe deploy/terraform/ en el proyecto?
  → SÍ: Modo modificación — ejecutar `make plan` para ver el estado actual, luego preguntar qué cambiar
  → NO: Modo creación desde cero — seguir al Paso 2
```

#### Paso 1.A — Modo modificación (proyecto existente)

Cuando `deploy/terraform/` ya existe, antes de proponer cambios el skill debe ejecutar `make plan` para mostrar al developer el diff real entre el código y AWS. Si solo necesita agregar un recurso nuevo, sugerir `vaas.infra.add` en su lugar.

**1.A.1 — Resolver ambiente**

Preguntar al developer qué ambiente inspeccionar. Default: `dev`. Valores aceptados: `dev`, `stg`, `prod`.

**1.A.2 — Detectar el AWS profile**

Leer `deploy/terraform/configuration/<env>/profile.tfvars` y extraer el valor de la línea no comentada `profile = "<X>"`.

- Si el archivo no existe, o la línea está comentada, o la asignación está ausente → usar `default`.
- Ejemplo: `profile = "dev"` → profile detectado = `dev`.

**1.A.3 — Prompt de credenciales y ejecución de `make plan`**

Aplicar el **Prompt de credenciales AWS** (ver sección superior del archivo) con el `<env>` resuelto en 1.A.1 y el `<profile>` resuelto en 1.A.2.

Según la opción elegida por el developer, terminás con uno de estos estados:

- Output de `make plan` disponible → continuar a 1.A.4.
- Sin output (cancelado, sso login falló, o plan falló) → continuar a 1.A.4 sin output.

**1.A.4 — Preguntar qué modificar**

Si hay output del plan, mostrárselo al developer y usar el diff como contexto para sugerir cambios concretos. Si no hay output, igual preguntar qué quiere modificar (sin el contexto del diff). Considerar nuevamente si `vaas.infra.add` es más apropiado para el cambio solicitado.

### Paso 2: Generar la estructura

Consultar `references/modules-catalog.md` para seleccionar los módulos correctos

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

5. **`Makefile`** — Comandos de Terraform
   - Usar `templates/makefile.md` como base

### Paso 4: Verificar placeholders y ejecutar plan inicial

Después de generar los archivos en modo creación, el skill cierra el flujo verificando que los `TODO_*` estén completos y ejecutando `make plan ENV=dev` para dejar al developer a un `make apply` de distancia.

**4.1 — Detectar `TODO_*` placeholders**

Ejecutar un grep recursivo de `TODO_` sobre los archivos de configuración generados:

```bash
grep -rn 'TODO_' deploy/terraform/configuration/ --include='*.tfvars' --include='*.conf'
```

- **Si hay matches** → listar al developer cada ocurrencia con formato `<path>:<line> <contenido>`, explicar brevemente qué tipo de valor falta (consultar `references/environment-config.md` para los valores correctos por ambiente) y **no continuar a 4.2**. Saltar directamente a 4.5 con el mensaje final y la lista de placeholders pendientes.
- **Si no hay matches** → continuar a 4.2.

**4.2 — Prompt de credenciales y ejecución de `make plan ENV=dev`**

Aplicar el **Prompt de credenciales AWS** (ver sección superior del archivo) con `env=dev` y el `<profile>` resuelto desde `deploy/terraform/configuration/dev/profile.tfvars`.

Según la opción elegida por el developer, terminás con uno de estos estados:

- Output de `make plan` disponible → continuar a 4.3.
- Sin output (cancelado, sso login falló, o plan falló) → continuar a 4.3 sin output.

**4.3 — Mensaje final al developer**

Cerrar el flujo con un resumen estructurado:

1. **Qué se creó** — lista de archivos generados, 1 línea cada uno.
2. **Estado del plan** — uno de:
   - "Plan ejecutado correctamente — revisá el output arriba antes de aplicar."
   - "Plan no ejecutado: completar los `TODO_*` listados y volver a correr `make plan ENV=dev` manualmente."
   - "Plan cancelado por el developer en el prompt de credenciales."
   - "Plan falló: ver error arriba y aplicar los pasos manuales sugeridos (e.g., `aws sso login --profile <X>`)."
3. **Próximo paso manual** — el developer ejecuta:
   ```bash
   make apply ENV=dev     # Crear los recursos en AWS (paso manual del developer)
   ```
4. **Sugerencias** — proponer `vaas.infra.cicd` si aún no tiene Jenkinsfile.

## Ejemplos

Consultar los archivos en `examples/` para ver implementaciones completas:
- `examples/example-ecs-service.md` — API Java/Spring con ECS service (como project-name)
- `examples/example-lambda.md` — Lambda function con EventBridge schedule
- `examples/example-scheduled-task.md` — ECS task programada

## Templates

Los archivos en `templates/` son plantillas base para cada archivo generado:
- `templates/main-tf.md` — main.tf
- `templates/inputs-tf.md` — inputs.tf
- `templates/locals-tf.md` — locals.tf
- `templates/makefile.md` — Makefile
- `templates/backend-conf.md` — backend.conf
