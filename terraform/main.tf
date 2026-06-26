# Camino de entrada: [Enricher] -> SNS topic (FIFO) -> SQS queue (FIFO) -> Lambda DPD

# 0. Log group de CloudWatch para la Lambda (retención por entorno).
module "cloudwatch" {
  source = "./modules/cloudwatch"

  cloudwatch_configuration = local.cloudwatch_configuration
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

# 5. Rol IAM + política para la Lambda.
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

# 7. Función Lambda DPD — imagen Docker desde ECR compartido.
module "lambda_dpd" {
  source               = "git@github.com:getvaas/tf_modules.git//lambda_docker"
  name                 = local.lambda_name
  memory_size          = var.lambda_memory_size
  timeout              = var.visibility_timeout
  iam_role_lambda_arn  = module.iam_lambda_dpd.iam_role_lambda_arn
  ecr_repository_uri   = module.ecr_dpd.ecr_repository_uri
  image_tag            = var.lambda_image_tag
  environment_variables = {
    "ENVIRONMENT"            = var.environment
    "AWS_REGION"             = var.aws_region
    "SECRET_NAME"            = var.secret_name
    "SNS_RESPONSE_TOPIC_ARN" = var.sns_response_topic_arn
    "BATCH_ROW_THRESHOLD"    = tostring(var.batch_row_threshold)
    "BATCH_JOB_QUEUE"        = module.batch_dpd.job_queue_arn
    "BATCH_JOB_DEFINITION"   = module.batch_dpd.job_definition_arn
  }
}

# 8. ECR compartido — Lambda y Batch usan la misma imagen Docker.
module "ecr_dpd" {
  source = "git@github.com:getvaas/tf_modules.git//ecr"
  name   = "${var.environment}-days-past-due-repository"
}

# 9. CloudWatch log group para el Batch job.
module "cloudwatch_batch" {
  source = "git@github.com:getvaas/tf_modules.git//cloudwatch"

  cloudwatch_configuration = {
    log_group_name    = "/aws/batch/${local.batch_name}"
    retention_in_days = var.log_retention_in_days != null ? var.log_retention_in_days : (var.environment == "dev" ? 1 : 7)
  }
}

# 10. IAM roles para el Batch job (job role + execution role).
module "iam_batch_dpd" {
  source = "./modules/iam_batch"

  job_role_name       = "${local.batch_name}-job-role"
  job_policy_name     = "${local.batch_name}-job-policy"
  execution_role_name = "${local.batch_name}-execution-role"

  job_policy_actions = [
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
  ]
}

# 11. Compute Environment + Job Queue + Job Definition.
module "batch_dpd" {
  source = "./modules/batch"

  environment          = var.environment
  name                 = local.batch_name
  ecr_image_uri        = "${module.ecr_dpd.ecr_repository_uri}:${var.lambda_image_tag}"
  job_role_arn         = module.iam_batch_dpd.job_role_arn
  execution_role_arn   = module.iam_batch_dpd.execution_role_arn
  cloudwatch_log_group = module.cloudwatch_batch.cloudwatch_log_group_name
  aws_region           = var.aws_region
  max_vcpus            = var.batch_max_vcpus
  job_vcpus            = var.batch_job_vcpus
  job_memory           = var.batch_job_memory_mb
  subnet_ids           = var.batch_subnet_ids
  security_group_ids   = var.batch_security_group_ids

  environment_variables = {
    "ENVIRONMENT"            = var.environment
    "AWS_REGION"             = var.aws_region
    "SECRET_NAME"            = var.secret_name
    "SNS_RESPONSE_TOPIC_ARN" = var.sns_response_topic_arn
    "BATCH_ROW_THRESHOLD"    = tostring(var.batch_row_threshold)
  }
}

# 4. Trigger SQS -> Lambda.
module "sqs_invoke" {
  source = "./modules/sqs_event_invoke_lambda"

  lambda_function_name               = module.lambda_dpd.lambda_function_name
  sqs_queue_arn                      = module.sqs.queue_arn
  batch_size                         = var.sqs_batch_size
  maximum_batching_window_in_seconds = var.sqs_batching_window_seconds
}

# 12. Topic SNS de respuesta — Lambda y Batch publican el resultado del cálculo DPD.
module "sns_response" {
  source      = "./modules/sns"
  environment = var.environment
  name        = "${local.name}_response"
  fifo_topic  = false
}

# 13. Cola SQS de respuesta + DLQ — downstream consume los resultados DPD desde acá.
module "sqs_response" {
  source               = "./modules/sqs"
  environment          = var.environment
  name                 = "${local.name}_response"
  fifo_queue           = false
  visibility_timeout   = 300
  sns_alarms_topic_arn = var.sns_alarms_topic_arn
}

# 14. Suscripción SNS respuesta -> SQS respuesta.
module "sns_response_subscription" {
  source        = "./modules/sns_subscription"
  environment   = var.environment
  sns_topic_arn = module.sns_response.sns_topic_arn
  queue_arn     = module.sqs_response.queue_arn
  queue_url     = module.sqs_response.queue_url
}
