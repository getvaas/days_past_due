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

# ─── SQS → Lambda trigger ───────────────────────────────────────────────────────

variable "sqs_batch_size" {
  type        = number
  default     = 1
  description = "Mensajes por invocación de Lambda (1–10). Con FIFO queues el máximo es 10."
}

variable "sqs_batching_window_seconds" {
  type        = number
  default     = 0
  description = "Segundos que SQS espera para acumular un batch antes de invocar (0–300). 0 = disparo inmediato."
}

# ─── Lambda ──────────────────────────────────────────────────────────────────────

variable "lambda_image_tag" {
  type        = string
  default     = "latest"
  description = "Tag de la imagen Docker en ECR usada por Lambda y Batch."
}

variable "lambda_memory_size" {
  type        = number
  default     = 512
  description = "Memoria asignada a la Lambda en MB."
}

variable "sns_response_topic_arn" {
  type        = string
  default     = ""
  description = "ARN del topic SNS donde la Lambda publica la respuesta enriquecida."
}

# ─── Batch ───────────────────────────────────────────────────────────────────────

variable "batch_row_threshold" {
  type        = number
  default     = 5000
  description = "Filas del loan tape a partir de las cuales se delega a AWS Batch."
}

variable "batch_max_vcpus" {
  type        = number
  default     = 16
  description = "Máximo de vCPUs del compute environment de Batch."
}

variable "batch_job_vcpus" {
  type        = string
  default     = "1"
  description = "vCPUs asignadas a cada job de Batch (formato string)."
}

variable "batch_job_memory_mb" {
  type        = number
  default     = 2048
  description = "Memoria en MB asignada a cada job de Batch."
}

variable "batch_subnet_ids" {
  type        = list(string)
  description = "Subnets privadas donde corre el compute environment de Batch."
}

variable "batch_security_group_ids" {
  type        = list(string)
  description = "Security groups del compute environment de Batch."
}
