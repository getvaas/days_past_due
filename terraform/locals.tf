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

  # ==========================================================================
  # Secrets
  # ==========================================================================
  # Claves esperadas dentro del JSON del secret de Payments.
  secrets = [
    "DATASOURCE___PAYMENTS_DB___URL",
    "DATASOURCE___PAYMENTS_DB___USERNAME",
    "DATASOURCE___PAYMENTS_DB___PASSWORD",
  ]
  auth0_secrets = [
    "url",
    "client_id",
    "client_secret",
    "vaas_header",
  ]

  # Valores crudos leídos del secret (mapa clave→valor).
  secret_values = module.secrets_manager.values

  # Conexión a la base de datos de Payments. Cada valor sale del secret.
  payments_db = {
    url      = local.secret_values["DATASOURCE___PAYMENTS_DB___URL"]
    username = local.secret_values["DATASOURCE___PAYMENTS_DB___USERNAME"]
    password = local.secret_values["DATASOURCE___PAYMENTS_DB___PASSWORD"]
  }
}
