# Estructura de Proyecto Terraform — Vaas

Esta es la estructura estándar para infraestructura Terraform en proyectos de Vaas.

---

## Estructura de directorios

```
<project>/
├── deploy/
│   └── terraform/
│       ├── main.tf                     # Orquestador principal
│       ├── inputs.tf                   # Variables de entrada del root module
│       ├── locals.tf                   # Valores computados y configuración local
│       ├── configuration/
│       │   ├── global.tfvars           # Valores compartidos entre ambientes
│       │   ├── dev/
│       │   │   ├── vars.tfvars         # Variables específicas de dev
│       │   │   ├── profile.tfvars      # Perfil AWS para dev
│       │   │   └── backend.conf        # Backend S3 para state de dev
│       │   ├── stg/
│       │   │   ├── vars.tfvars
│       │   │   ├── profile.tfvars
│       │   │   └── backend.conf
│       │   └── prod/
│       │       ├── vars.tfvars
│       │       ├── profile.tfvars
│       │       └── backend.conf
│       ├── iam/                        # Módulo local de IAM
│       │   └── iam_orchestrator.tf
│       ├── ecr/                        # Módulo local de ECR
│       │   └── ecr_orchestrator.tf
│       ├── ecs/                        # Módulo local de ECS (legacy, se usa tf_modules en main.tf)
│       │   └── ecs_orchestrator.tf
│       ├── cloudwatch/                 # Módulo local de CloudWatch
│       │   └── cloudwatch_orchestrator.tf
│       ├── s3/                         # Módulo local de S3 (si aplica)
│       │   ├── main.tf
│       │   ├── input.tf
│       │   └── output.tf
│       ├── sqs/                        # Módulo local de SQS (si aplica)
│       │   ├── sqs_orchestrator.tf
│       │   ├── inputs.tf
│       │   └── outputs.tf
│       ├── sns_sqs/                    # Módulo local de SNS+SQS (si aplica)
│       │   ├── main.tf
│       │   ├── input.tf
│       │   └── output.tf
│       ├── parameter_store/            # Módulo local de Parameter Store (si aplica)
│       ├── secret_manager/             # Módulo local de Secrets Manager (si aplica)
│       └── user/                       # Módulo local de IAM Users (si aplica)
│           ├── main.tf
│           ├── input.tf
│           └── output.tf
├── Makefile                            # Shortcuts: make plan ENV=dev
├── Dockerfile
├── Jenkinsfile
└── .github/
    └── workflows/
        └── github-actions.yaml
```

---

## Descripción de cada archivo

### `main.tf` — Orquestador

El archivo principal que:
1. Configura el backend S3 para el state
2. Configura el provider AWS con default_tags
3. Opcionalmente lee secretos de Secrets Manager como data sources
4. Importa todos los módulos locales y externos

**Patrón**:
```hcl
# Backend
terraform {
  backend "s3" {}
}

# Provider
provider "aws" {
  region  = var.aws_region
  profile = var.profile
  default_tags {
    tags = {
      Environment   = var.environment
      Author        = var.author
      CostCenter    = var.cost_center
      ProjectName   = var.project_name_camel_case
      ComponentName = var.component_name_camel_case
      GithubRepo    = var.github_repository
    }
  }
}

# Módulos
module "iam_orchestrator" {
  source           = "git@github.com:getvaas/tf_modules.git//iam"
  iam_orchestrator = local.iam_orchestrator
}

module "ecr_orchestrator" {
  source           = "git@github.com:getvaas/tf_modules.git//ecr"
  ecr_orchestrator = local.ecr_orchestrator
}

module "ecs_service" {
  source = "git@github.com:getvaas/tf_modules.git//ecs_service"
  # ... inputs del servicio
  depends_on = [module.iam_orchestrator, module.ecr_orchestrator]
}
```

### `inputs.tf` — Variables

Define TODAS las variables que reciben valor desde los `.tfvars`. Categorías típicas:
- **Infraestructura**: environment, aws_region, vpc_id, subnets, security groups
- **Naming**: project_name variants (CamelCase, snake_case), component_name
- **Metadata**: author, cost_center, github_repository
- **Secrets**: ARNs de Secrets Manager
- **ALB**: listener ARNs, capacity_provider
- **Extras**: environment_variables (map), profile

### `locals.tf` — Configuración computada

Define objetos locales que configuran cada módulo. Ejemplo:
- `local.iam_orchestrator` — config de roles y policies
- `local.ecr_orchestrator` — nombre del repo ECR
- `local.ecs_cluster_configuration` — CPU, memoria, versión
- `local.cloudwatch_configuration` — log group, retention
- `local.target_group_configuration` — puertos, health check path

### `configuration/global.tfvars` — Valores globales

Valores que **no cambian entre ambientes**:
```hcl
project_name_camel_case         = "MyProject"
project_name_snake_case         = "my_project"
project_name_acronym_snake_case = "my_project"
component_name_camel_case       = "Api"
component_name_snake_case       = "api"
author                          = "team@getvaas.com"
cost_center                     = "MyProjectApi"
github_repository               = "my-project-api"
parameter_store_application_name = "Vaas-MyProjectApi"
```

### `configuration/<env>/vars.tfvars` — Valores por ambiente

Valores **específicos de cada ambiente**:
```hcl
environment           = "dev"
environment_full_name = "Development"
aws_region            = "us-east-1"
vpc_id                = "vpc-..."
capacity_provider     = "dev_arm_large_one_cluster_capacity_provider"
# ARNs de ALB, subnets, secrets manager, etc.
```

### `configuration/<env>/backend.conf` — Backend S3

```
bucket         = "<prefix>-<env>-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "<env>-terraform-lock-table"
key            = "<project-name>/terraform.tfstate"
```

### `configuration/<env>/profile.tfvars` — Perfil AWS

```hcl
# Este archivo configura el perfil de AWS CLI. Descomentarlo solo para ejecución local.
# profile = "dev"
```

---

## Módulos locales

Los módulos locales son wrappers simples que encapsulan recursos relacionados. Patrones comunes:

### Patrón "Orchestrator" (un solo archivo)
Usado para módulos simples como IAM, ECR, CloudWatch:
```
iam/
└── iam_orchestrator.tf    # Variables + Resources + Outputs en un solo archivo
```

### Patrón "Standard" (tres archivos)
Usado para módulos más complejos como S3, SQS, user:
```
s3/
├── main.tf     # Resources
├── input.tf    # Variables
└── output.tf   # Outputs
```

---

## Makefile

El Makefile proporciona shortcuts para los comandos de Terraform:

```makefile
.PHONY: all
LOCATION=deploy/terraform
ENV?=dev

help:
	@echo "Execute: make <plan|apply> ENV=<(dev)|stg|prod>"

plan:
	cd $(LOCATION) && \
	rm -rf .terraform* && \
	terraform init -backend-config=configuration/$(ENV)/backend.conf \
	  -backend-config=configuration/$(ENV)/profile.tfvars && \
	terraform plan \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars

apply:
	cd $(LOCATION) && \
	rm -rf .terraform* && \
	terraform init -backend-config=configuration/$(ENV)/backend.conf \
	  -backend-config=configuration/$(ENV)/profile.tfvars && \
	terraform apply \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars

clean:
	cd $(LOCATION) && \
	rm -rf .terraform*

just-plan:
	cd $(LOCATION) && \
	terraform plan \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars
```

**Uso**:
```bash
make plan ENV=dev      # Ver cambios pendientes en dev
make apply ENV=dev     # Aplicar cambios en dev
make plan ENV=prod     # Ver cambios pendientes en prod
make clean             # Limpiar archivos temporales de Terraform
```
