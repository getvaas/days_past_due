locals {
  # ej. dev_days_past_due  → la cola queda dev_days_past_due_fifo_queue.fifo
  name = "${var.environment}_${var.project_name_snake_case}"

  # Nombre de la Lambda (convención ${env}-${kebab}-lambda).
  lambda_name = "${var.environment}-${replace(var.project_name_snake_case, "_", "-")}-lambda"

  # Nombre base del Batch job (convención ${env}-${kebab}-batch).
  batch_name = "${var.environment}-${replace(var.project_name_snake_case, "_", "-")}-batch"

  cloudwatch_configuration = {
    log_group_name    = "/aws/lambda/${local.lambda_name}"
    retention_in_days = var.log_retention_in_days != null ? var.log_retention_in_days : (var.environment == "dev" ? 1 : 7)
  }

  # Topic de entrada: el del Enricher si se pasó su ARN, o el creado acá.
  # one(...) devuelve null sin error cuando el módulo tiene count = 0.
  inbound_topic_arn = var.inbound_sns_topic_arn != "" ? var.inbound_sns_topic_arn : one(module.sns_inbound[*].sns_topic_arn)

}
