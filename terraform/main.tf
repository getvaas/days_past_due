# Camino de entrada: [Enricher] -> SNS topic (FIFO) -> SQS queue (FIFO) -> Lambda DPD

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

# 5. Bucket S3 para loan tapes (input y output de la Lambda).
#    La Lambda lee el loan tape desde input_file y escribe el resultado en output_file,
#    ambos paths apuntan a este bucket.
module "s3_loan_tape" {
  source      = "git@github.com:getvaas/tf_modules.git//s3"
  bucket_name = "days-past-due-loan-tape"
  environment = var.environment
}

# 6. Rol IAM + política para la Lambda.
module "iam_lambda_dpd" {
  source = "git@github.com:getvaas/tf_modules.git//iam_lambda"
  iam_configuration = {
    role_lambda_name   = "${var.environment}-days-past-due-lambda-role"
    policy_lambda_name = "${var.environment}-days-past-due-lambda-policy"
    policy_lambda_actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "secretsmanager:GetSecretValue",
      "sns:Publish",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "batch:SubmitJob",
    ]
  }
}

# 7. Función Lambda DPD.
module "lambda_dpd" {
  source              = "git@github.com:getvaas/tf_modules.git//lambda"
  name                = local.lambda_name
  handler             = "dpd.lambda_handler.handler"
  runtime             = "python3.11"
  memory_size         = var.lambda_memory_size
  timeout             = var.visibility_timeout
  iam_role_lambda_arn = module.iam_lambda_dpd.iam_role_lambda_arn
  s3_code_bucket      = var.lambda_code_bucket
  s3_code_key         = var.lambda_code_key
  environment_variables = {
    "ENVIRONMENT"            = var.environment
    "AWS_REGION"             = var.aws_region
    "PAYMENTS_SECRET_NAME"   = var.payments_secret_name
    "SNS_RESPONSE_TOPIC_ARN" = var.sns_response_topic_arn
    "BATCH_ROW_THRESHOLD"    = tostring(var.batch_row_threshold)
    "BATCH_JOB_QUEUE"        = var.batch_job_queue
    "BATCH_JOB_DEFINITION"   = var.batch_job_definition
  }
}

# 4. Trigger SQS -> Lambda.
module "sqs_invoke" {
  source = "./modules/sqs_event_invoke_lambda"

  lambda_function_name = module.lambda_dpd.lambda_function_name
  sqs_queue_arn        = module.sqs.queue_arn
}
