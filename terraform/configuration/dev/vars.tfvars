environment = "dev"
aws_region  = "us-east-1"

# Topic SNS para alarmas CloudWatch de la cola. Vacío = sin alarmas en esta fase.
sns_alarms_topic_arn = "arn:aws:sns:us-east-1:052650215423:dev-elisir-alarms-topic"

# Vacío = se crea el topic de entrada acá.
# Si el Enricher ya posee el topic, poner su ARN (FIFO) y NO se crea uno nuevo.
inbound_sns_topic_arn = ""

# Vacío = no se crea el trigger todavía (la Lambda aún no existe).
# Cuando la Lambda esté desplegada, poner su nombre y re-aplicar.
lambda_function_name = ""

# Secret de Secrets Manager con las credenciales de la base Payments (JSON).
# CONFIRMAR el nombre/ARN real del secret en la cuenta dev.
payments_secret_name = "dev/payments/datasource"
