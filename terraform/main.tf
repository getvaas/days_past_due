module "lambda_container" {
  source                = "git@github.com:getvaas/tf_modules.git//lambda_container"
  name                  = local.lambda_configuration.name
  environment           = var.environment
  memory_size           = local.lambda_configuration.memory_size
  architectures         = local.lambda_configuration.architectures
  timeout               = local.global_timeout
  ephemeral_storage     = var.ephemeral_storage
  environment_variables = var.environment_variables
  subnet_ids            = var.subnet_private_ids
  security_group_ids    = [var.security_group_id]
  profile               = var.profile
  iam_role_name      = local.lambda_configuration.iam_configuration.role_lambda_name
  iam_policy_name    = local.lambda_configuration.iam_configuration.policy_lambda_name
  iam_policy_actions = local.lambda_configuration.iam_configuration.policy_lambda_actions
  log_retention_in_days = local.cloudwatch_configuration.retention_in_days
}
module "sqs" {
  source             = "git@github.com:getvaas/tf_modules.git//sqs"
  name               = local.sqs_configuration.name
  visibility_timeout = local.sqs_configuration.visibility_timeout
  message_retention_seconds = local.sqs_configuration.message_retention_seconds
  sns_topic_arns = [var.input_sns]
}

module "sqs_invoke" {
  source = "./modules/sqs_event_invoke_lambda"
  lambda_function_name               = module.lambda_container.lambda_function_name
  sqs_queue_arn                      = module.sqs.queue_arn
}

module "secrets_manager" {
  source      = "git@github.com:getvaas/tf_modules.git//secret_bundle"
  environment = var.environment
  project     = var.project_name_snake_case
  secret_keys = [local.secrets_manager_configuration.keys]
}

module "batch" {
  source      = "git@github.com:getvaas/tf_modules.git//batch?ref=feature/batch-module"
  ecr_image_uri = module.lambda_container.ecr_repository_uri
  environment   = var.environment
  name          = local.batch_configuration.name
  security_group_ids = [var.security_group_id]
  log_retention_in_days = local.cloudwatch_configuration.retention_in_days
  job_memory = local.batch_configuration.memory_size
  job_policy_name = local.batch_configuration.iam_configuration.policy_batch_name
  job_vcpus = local.batch_configuration.v_cpus
  job_policy_actions = [local.batch_configuration.iam_configuration.policy_batch_actions]
  subnet_ids = [var.subnet_private_ids]
  job_role_name = local.batch_configuration.iam_configuration.role_batch_name
  architectures = [local.batch_configuration.architectures]
}