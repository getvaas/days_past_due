# ─── Entorno / AWS ────────────────────────────────────────────────────────────

variable "environment" {
  type        = string
  description = "Nombre del entorno (dev/stg/prod)."
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "profile" {
  type    = string
  default = ""
}

# ─── Naming / tagging ───────────────────────────────────────────────────────────

variable "project_name_camel_case" {
  type    = string
  default = "days-past-due"
}

variable "project_name_snake_case" {
  type    = string
  default = "days_past_due"
}

variable "component_name_camel_case" {
  type    = string
  default = ""
}

variable "author" {
  type    = string
  default = ""
}

variable "cost_center" {
  type    = string
  default = ""
}

variable "github_repository" {
  type    = string
  default = ""
}

# ─── Cola / mensajería ──────────────────────────────────────────────────────────

variable "visibility_timeout" {
  type        = number
  default     = 900
  description = "Visibility timeout de la cola en segundos. Debe ser >= timeout de la Lambda."
}

variable "content_based_deduplication" {
  type        = bool
  default     = true
  description = "Dedup por contenido en la cola/topic FIFO. Si es false, el productor debe enviar MessageDeduplicationId."
}

variable "sns_alarms_topic_arn" {
  type        = string
  default     = ""
  description = "Topic SNS para alarmas CloudWatch de la cola. Vacío = sin alarmas."
}

variable "log_retention_in_days" {
  type        = number
  default     = null
  description = "Retención del log group de la Lambda. null = 1 día en dev, 7 en el resto."
}

# ─── Secrets ────────────────────────────────────────────────────────────────────

variable "payments_secret_name" {
  type        = string
  description = "Nombre/ARN del secret de Secrets Manager con las credenciales de la base Payments (valor JSON)."
}

variable "inbound_sns_topic_arn" {
  type        = string
  default     = ""
  description = "ARN del topic de entrada si lo posee el Enricher. Vacío = se crea uno acá."
}

variable "lambda_function_name" {
  type        = string
  default     = ""
  description = "Nombre de la Lambda a disparar. Vacío = no se crea el trigger (la Lambda aún no existe)."
}
