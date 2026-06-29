# Template: backend.conf

Configuración del backend S3 para el state de Terraform. Un archivo por ambiente.

## Template

```
bucket         = "{{bucket_prefix}}-{{env}}-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "{{env}}-terraform-lock-table"
key            = "{{project_name}}/terraform.tfstate"
```

## Variables a reemplazar

| Placeholder | Descripción | Ejemplo |
|------------|-------------|---------|
| `{{bucket_prefix}}` | Prefijo del bucket (único por organización) | `6fc5w786` |
| `{{env}}` | Nombre del ambiente | `dev`, `stg`, `prod` |
| `{{project_name}}` | Nombre del proyecto (kebab-case) | `project-name` |

## Ejemplo para dev

```
bucket         = "6fc5w786-dev-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "dev-terraform-lock-table"
key            = "my-project/terraform.tfstate"
```

## Ejemplo para prod

```
bucket         = "6fc5w786-prod-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "prod-terraform-lock-table"
key            = "my-project/terraform.tfstate"
```

## Notas

- El `bucket_prefix` es compartido por todos los proyectos en la organización. Consultar al equipo de plataforma si no lo conoces.
- El `dynamodb_table` se usa para locking — previene que dos personas apliquen cambios al mismo tiempo.
- El `key` debe ser único por proyecto dentro del bucket.
- `encrypt = true` asegura que el state se almacene encriptado en S3.
