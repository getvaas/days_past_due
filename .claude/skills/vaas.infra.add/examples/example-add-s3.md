# Ejemplo: Agregar bucket S3 a proyecto existente

## Contexto

El proyecto `project-name` ya tiene infraestructura con ECS service. El developer necesita un nuevo bucket S3 para almacenar reportes exportados.

## Archivos modificados

### 1. Crear `deploy/terraform/s3/` (módulo local nuevo)

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

### 2. Agregar módulo en `deploy/terraform/main.tf`

```hcl
module "s3_reports" {
  source        = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name   = "project-name-reports"
  bucket_prefix = "gf78999f"
  environment   = var.environment
}
```

Y pasar el nombre del bucket al servicio ECS:
```hcl
module "ecs_service" {
  # ... inputs existentes ...
  environment_variables = merge(var.environment_variables, {
    # ... variables existentes ...
    "REPORTS_BUCKET" = module.s3_reports.bucket_name
  })
}
```

### 3. Actualizar permisos IAM en `deploy/terraform/locals.tf`

Agregar a `ecs_policy_actions`:
```hcl
"s3:GetObject",
"s3:ListBucket",
"s3:PutObject",
"s3:DeleteObject",
```

### Verificar

```bash
make plan ENV=dev
# Debería mostrar: Plan: 4 to add (bucket, public access block, versioning, ownership)
```
