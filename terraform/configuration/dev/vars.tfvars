environment = "dev"
aws_region  = "us-east-1"

# Topic SNS para alarmas CloudWatch de la cola.
sns_alarms_topic_arn = "arn:aws:sns:us-east-1:052650215423:dev-elisir-alarms-topic"

# Vacío = se crea el topic de entrada acá.
# Si el Enricher ya posee el topic, poner su ARN (FIFO) y NO se crea uno nuevo.
inbound_sns_topic_arn = ""

# Secret de Secrets Manager con las credenciales de la base Payments (JSON).
payments_secret_name = "dev/payments/datasource"

# ─── Lambda ──────────────────────────────────────────────────────────────────────
lambda_image_tag   = "latest"
lambda_memory_size = 512

# ARN del topic SNS donde la Lambda publica la respuesta enriquecida.
# Completar cuando se cree el topic de respuesta.
sns_response_topic_arn = ""

# ─── Batch ───────────────────────────────────────────────────────────────────────
batch_row_threshold      = 5000
batch_max_vcpus          = 16
batch_job_vcpus          = "1"
batch_job_memory_mb      = 2048
batch_subnet_ids         = [
  "subnet-023b07c277cb886cb",
  "subnet-08ccd313039482327",
  "subnet-06f814e9677a7a796",
]
batch_security_group_ids = ["sg-0031cc45b05258c36"]
