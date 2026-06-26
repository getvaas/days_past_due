# Vaas Environment Configuration

Valores de infraestructura por ambiente. Estos valores son constantes compartidas que el developer necesita para configurar Terraform.

---

## Cuentas AWS

| Ambiente | Account ID | Uso |
|----------|-----------|-----|
| dev | `052650215423` | Desarrollo |
| stg | `052650215423` | Staging (misma cuenta que dev) |
| prod | `387023001980` | Producción |

---

## Región

| Tipo | Región |
|------|--------|
| Primary | `us-east-1` |
| DR | `us-east-2` |

---

## VPC IDs

| Ambiente | VPC ID |
|----------|--------|
| dev / stg (non-prod) | `vpc-0fb53b76f02cbe650` |
| prod | `vpc-0a487bca114ad676a` |

---

## ECS Clusters

| Ambiente | Cluster Name |
|----------|-------------|
| dev | `dev-one-cluster` |
| stg | `stg-one-cluster` |
| prod | `prod-one-cluster` |

---

## Capacity Providers

| Tipo | Patrón |
|------|--------|
| ARM (default) | `<env>_arm_one_cluster_capacity_provider` |
| x86 | `<env>_x86_one_cluster_capacity_provider` |

Ejemplos:
- dev ARM: `dev_arm_one_cluster_capacity_provider`
- stg ARM: `stg_arm_one_cluster_capacity_provider`
- prod ARM: `prod_arm_one_cluster_capacity_provider`

---

## ALB Public HTTPS Listener ARNs

| Ambiente | ARN |
|----------|-----|
| dev | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Dev-Pub-AppLoadBalancer/7bac3213d92ada71/49839fb562ea4760` |
| stg | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Stg-Pub-AppLoadBalancer/da5c1c77ad16c678/99000e007fffdcda` |
| prod | `arn:aws:elasticloadbalancing:us-east-1:387023001980:listener/app/LB-Prod-Pub-AppLoadBalancer/209f5e16fc607827/499f69d69fc261db` |

---

## ALB Internal HTTPS Listener ARNs

| Ambiente | ARN |
|----------|-----|
| dev | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Dev-Int-AppLoadBalancer/a133c9d3d021bab2/28f086caa7cafd8c` |
| stg | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Stg-Int-AppLoadBalancer/76219202b94a2e2e/bfe26b7a694480b2` |
| prod | `arn:aws:elasticloadbalancing:us-east-1:387023001980:listener/app/LB-Prod-Int-AppLoadBalancer/7a3fd49c4c118cd5/50a6a5a1fda6f177` |

---

## ALB Public HTTP Listener ARNs

| Ambiente | ARN |
|----------|-----|
| dev | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Dev-Pub-AppLoadBalancer/7bac3213d92ada71/b9bf246899185baf` |
| stg | `arn:aws:elasticloadbalancing:us-east-1:052650215423:listener/app/LB-Stg-Pub-AppLoadBalancer/da5c1c77ad16c678/e58b0981902238c1` |
| prod | `arn:aws:elasticloadbalancing:us-east-1:387023001980:listener/app/LB-Prod-Pub-AppLoadBalancer/209f5e16fc607827/26a3a1c214436ae2` |

---

## Terraform State Backends

| Campo | Patrón |
|-------|--------|
| Bucket | `<prefix>-<env>-terraform-states-bucket` |
| Lock table | `<env>-terraform-lock-table` |
| Region | `us-east-1` |
| Key | `<project-name>/terraform.tfstate` |
| Encrypt | `true` |

Ejemplo para dev (como project-name):
```
bucket         = "6fc5w786-dev-terraform-states-bucket"
encrypt        = true
region         = "us-east-1"
dynamodb_table = "dev-terraform-lock-table"
key            = "my-project/terraform.tfstate"
```

**Nota**: El prefijo del bucket (e.g. `6fc5w786`) es específico de cada proyecto. Consultar al equipo de plataforma o usar un prefijo único.

---

## SNS Alarm Topics

| Ambiente | ARN |
|----------|-----|
| dev | `arn:aws:sns:us-east-1:052650215423:dev-borbotones-alarms-topic` |
| stg | `arn:aws:sns:us-east-1:052650215423:stg-borbotones-alarms-topic` |
| prod | `arn:aws:sns:us-east-1:387023001980:prod-borbotones-alarms-topic` |

---

## CloudWatch Log Retention

| Ambiente | Retención |
|----------|-----------|
| dev | 1-7 días |
| stg | 7 días |
| prod | 30 días |

---

## Jenkins Credentials

| Ambiente | Credential ID |
|----------|--------------|
| dev / stg | `jenkins-aws-development` |
| prod | `jenkins-aws-production-core` |

---

## ECR Repository URLs

| Ambiente | Base URL |
|----------|----------|
| dev / stg | `052650215423.dkr.ecr.us-east-1.amazonaws.com` |
| prod | `387023001980.dkr.ecr.us-east-1.amazonaws.com` |

---

## Tags por defecto (provider default_tags)

Todas las infraestructuras de Vaas deben incluir estos tags en el provider de AWS:

```hcl
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
```

---

## Subnets

### Non-prod (dev/stg)

**Public subnets**:
- `subnet-097e32efe6d1fafc8`
- `subnet-0b970dbd3dbcbb202`
- `subnet-0f5d55e60f412f983`
- `subnet-0f2397faef6915df7`
- `subnet-0478541f57d4a0fe0`
- `subnet-0cc4764c8f7aa9a80`

**Private subnets**:
- `subnet-023b07c277cb886cb`
- `subnet-08ccd313039482327`
- `subnet-06f814e9677a7a796`
- `subnet-0302f0c97c8844ebf`
- `subnet-0e0bb17925802cb31`
- `subnet-0041213af3241cec1`

### Prod

**Public subnets**:
- `subnet-00d57a90dc22f12d0`
- `subnet-0c5a48b3abe0f29e2`
- `subnet-0123e11a3b5fbac22`
- `subnet-0a7095ad64c955aec`
- `subnet-0ab5051f052837553`
- `subnet-050e8266ad9f4278b`

**Private subnets**:
- `subnet-04e4f33eb33b37abf`
- `subnet-061e29a850d0a8ebe`
- `subnet-0814af59be8eb4795`
- `subnet-0953423c8506359ce`
- `subnet-02d4c47a96bc07de5`
- `subnet-070fa7a822f0f8405`

---

## Security Groups

| Ambiente | Security Group ID |
|----------|------------------|
| dev | `sg-0031cc45b05258c36` |
| stg | `sg-04da060b6eff07339` |
| prod | `sg-0bae023cc4d240d7a` |
