# Ejemplo: Agregar Parameter Store a proyecto existente

## Contexto

El proyecto `documents-api` necesita almacenar configuración de la aplicación en AWS Parameter Store (valores no secretos como URLs, feature flags, timeouts).

## Archivos modificados

### 1. Agregar módulo en `deploy/terraform/main.tf`

```hcl
module "parameter_store" {
  source = "git@github.com:getvaas/tf_modules.git//parameter_store"
  prefix = "/${var.environment}/${var.parameter_store_application_name}"
  parameter_store_configuration = {
    "feature_new_ui"     = "false"
    "max_upload_size_mb" = "50"
    "webhook_timeout_ms" = "5000"
  }
}
```

### 2. Agregar variable en `deploy/terraform/inputs.tf` (si no existe)

```hcl
variable "parameter_store_application_name" {
  type        = string
  description = "Application name for Parameter Store prefix"
}
```

### 3. Agregar valor en `deploy/terraform/configuration/global.tfvars`

```hcl
parameter_store_application_name = "Vaas-DocumentsApi"
```

### 4. Pasar la configuración al servicio ECS

Opción A — El servicio lee de Parameter Store directamente (necesita el prefijo):
```hcl
module "ecs_service" {
  environment_variables = merge(var.environment_variables, {
    # ... variables existentes ...
    "PARAMETER_STORE_PREFIX" = "/${var.environment}/${var.parameter_store_application_name}"
  })
}
```

Opción B — Pasar valores individuales como env vars:
```hcl
module "ecs_service" {
  environment_variables = merge(var.environment_variables, {
    "MAX_UPLOAD_SIZE_MB" = "50"
    "WEBHOOK_TIMEOUT_MS" = "5000"
  })
}
```

### 5. Actualizar permisos IAM en `deploy/terraform/locals.tf`

Agregar a `ecs_policy_actions`:
```hcl
"ssm:GetParametersByPath",
"ssm:GetParameter",
```

### Verificar

```bash
make plan ENV=dev
# Debería mostrar: Plan: 3 to add (3 SSM parameters)
```

### Notas

- Los parámetros en Parameter Store son de tipo String (no SecureString). Para secretos, usar Secrets Manager.
- El prefijo sigue el patrón `/<env>/<app-name>/` por convención de Vaas.
- Los valores se pueden cambiar directamente en Terraform o desde AWS Console.
