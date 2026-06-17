# Terraform — Infraestructura SQS (Payments Expand)

Infraestructura **autocontenida** (sin dependencias de otros repos) para la cola de entrada de DaysPastDue.

Camino de entrada: `[Enricher] → SNS topic (FIFO) → SQS queue (FIFO) → (trigger) → Lambda DPD`.

## Alcance

Esta carpeta crea **solo la cola SQS de entrada y su trigger**:

- Topic SNS FIFO de entrada (`${env}_days_past_due_sns_topic.fifo`) — opcional, ver abajo.
- Cola SQS FIFO (`${env}_days_past_due_fifo_queue.fifo`) + DLQ + redrive (`maxReceiveCount = 3`).
- Suscripción SNS→SQS + policy que habilita a SNS a enviar a la cola.
- Event source mapping SQS→Lambda (`batch_size = 1`) + permiso de invocación. **Condicional**: solo se crea
  si `lambda_function_name` está seteado.
- Log group de CloudWatch (`/aws/lambda/${env}-days-past-due-lambda`) con retención por entorno, donde la
  Lambda escribirá sus logs.
- Lectura del secret de Payments en Secrets Manager y armado de la conexión a la base
  (`locals.payments_db` = url/username/password). El secret **no se crea**, se asume existente.

**Fuera de alcance** (fases siguientes): la Lambda en sí (Dockerfile/imagen), su rol IAM, VPC, y el topic SNS
de respuesta.

## Estructura

```
terraform/
├── provider.tf · variables.tf · locals.tf · main.tf · outputs.tf
├── configuration/
│   ├── global.tfvars
│   └── dev/{backend.conf, vars.tfvars}
└── modules/                  # módulos locales, autocontenidos
    ├── sqs/ · sns/ · sns_subscription/ · sqs_event_invoke_lambda/ · cloudwatch/ · secrets_manager/
```

## Uso

```bash
cd terraform
terraform fmt -recursive
terraform init -backend-config=configuration/dev/backend.conf
terraform validate
terraform plan  -var-file=configuration/global.tfvars -var-file=configuration/dev/vars.tfvars
terraform apply -var-file=configuration/global.tfvars -var-file=configuration/dev/vars.tfvars
```

> Requiere Terraform >= 1.3 y credenciales AWS de la cuenta `dev`. Los valores de
> `configuration/dev/backend.conf` (bucket/lock del state) deben confirmarse antes del `init`.

## Variables clave

| Variable | Default | Nota |
|----------|---------|------|
| `payments_secret_name` | (dev tfvars) | Nombre/ARN del secret JSON de Payments en Secrets Manager. **Confirmar el real.** |
| `inbound_sns_topic_arn` | `""` | Vacío = se crea el topic acá. Si el Enricher ya lo posee, poné su ARN (FIFO) y no se crea uno nuevo. |
| `lambda_function_name` | `""` | Vacío = no se crea el trigger (la Lambda aún no existe). Setealo y re-aplicá cuando exista. |
| `sns_alarms_topic_arn` | (dev tfvars) | Vacío = sin alarmas CloudWatch. |
| `visibility_timeout` | `900` | Debe ser ≥ el timeout de la Lambda. |
| `content_based_deduplication` | `true` | FIFO: con `true` el Enricher no necesita `MessageDeduplicationId` (sí `MessageGroupId`). |

## Pendientes para la fase de la Lambda (documentados, no creados acá)

- **Rol IAM de la Lambda**: `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` sobre
  `output.queue_arn`; `sns:Publish` sobre el topic de respuesta; y `secretsmanager:GetSecretValue` sobre
  `module.secrets_manager.secret_arn` (la base Payments).
- **Secrets en el state**: leer el secret con un `data source` deja sus valores en el `terraform.tfstate`
  (que ya está cifrado en S3). Tenerlo en cuenta.
- **Topic SNS de respuesta** (`SNS_RESPONSE_TOPIC_ARN`, usado por `dpd/sns_publisher.py`): referenciar o crear.
- **VPC**: subnets + security group para acceso a MySQL (no aplica a la cola).
- **Productor FIFO**: el Enricher debe enviar `MessageGroupId` en cada publicación.
