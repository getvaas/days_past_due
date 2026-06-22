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
# Bucket y clave donde el pipeline CI/CD sube el ZIP de la Lambda.
lambda_code_bucket = "TODO_lambda_code_bucket"
lambda_code_key    = "days-past-due/latest.zip"
lambda_memory_size = 512

# ARN del topic SNS donde la Lambda publica la respuesta enriquecida.
# Completar cuando se cree el topic de respuesta.
sns_response_topic_arn = ""

# ─── Batch ───────────────────────────────────────────────────────────────────────
batch_row_threshold  = 5000
batch_job_queue      = ""
batch_job_definition = ""
