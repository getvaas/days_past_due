variable "environment" {
  type = string
}

variable "name" {
  type        = string
  description = "Prefijo del nombre de la cola (ej. dev_days_past_due)."
}

variable "visibility_timeout" {
  type        = number
  description = "Visibility timeout en segundos. Recomendado >= timeout de la Lambda."
}

variable "message_retention_seconds" {
  type    = number
  default = 86400
}

variable "max_message_size" {
  type    = number
  default = 262144
}

variable "max_receive_count" {
  type        = number
  default     = 3
  description = "Recepciones antes de mover el mensaje a la DLQ."
}

variable "avoid_dl_queue" {
  type    = bool
  default = false
}

variable "fifo_queue" {
  type    = bool
  default = false
}

variable "content_based_deduplication" {
  type        = bool
  default     = true
  description = "Solo aplica a colas FIFO."
}

variable "sns_alarms_topic_arn" {
  type        = string
  default     = ""
  description = "Topic SNS para alarmas CloudWatch. Vacío = sin alarmas."
}
