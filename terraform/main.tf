# Camino de entrada: [Enricher] -> SNS topic (FIFO) -> SQS queue (FIFO) -> Lambda DPD
#
# Alcance de esta entrega: cola SQS + trigger. La Lambda, su rol IAM, VPC y el
# topic SNS de respuesta quedan fuera (ver plan / README de infra).

# 0. Log group de CloudWatch para la Lambda (retención por entorno).
module "cloudwatch" {
  source = "./modules/cloudwatch"

  cloudwatch_configuration = local.cloudwatch_configuration
}

# Secret con las credenciales de la base Payments (se lee, no se crea).
# Sus valores se usan en locals.payments_db para armar la conexión.
module "secrets_manager" {
  source = "./modules/secrets_manager"

  secret_name = var.payments_secret_name
}

# 1. Topic SNS de entrada. Solo se crea si el Enricher no posee ya uno
#    (var.inbound_sns_topic_arn vacío).
module "sns_inbound" {
  count  = var.inbound_sns_topic_arn == "" ? 1 : 0
  source = "./modules/sns"

  environment                 = var.environment
  name                        = var.project_name_snake_case
  fifo_topic                  = true
  content_based_deduplication = var.content_based_deduplication
}

# 2. Cola FIFO + DLQ + redrive (+ alarmas si hay topic de alarmas).
module "sqs" {
  source = "./modules/sqs"

  environment                 = var.environment
  name                        = local.name
  fifo_queue                  = true
  content_based_deduplication = var.content_based_deduplication
  visibility_timeout          = var.visibility_timeout
  sns_alarms_topic_arn        = var.sns_alarms_topic_arn
}

# 3. Suscripción SNS -> SQS + policy que habilita a SNS a enviar a la cola.
module "sns_subscription" {
  source = "./modules/sns_subscription"

  environment   = var.environment
  sns_topic_arn = local.inbound_topic_arn
  queue_arn     = module.sqs.queue_arn
  queue_url     = module.sqs.queue_url
}

# 4. Trigger SQS -> Lambda. Solo si ya existe la Lambda (var.lambda_function_name).
module "sqs_invoke" {
  count  = var.lambda_function_name != "" ? 1 : 0
  source = "./modules/sqs_event_invoke_lambda"

  lambda_function_name = var.lambda_function_name
  sqs_queue_arn        = module.sqs.queue_arn
}
