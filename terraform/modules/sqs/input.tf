variable "environment" {
  type = string
}

variable "name" {
  type = string
}

variable "fifo_queue" {
  type    = bool
  default = false
}

variable "content_based_deduplication" {
  type    = bool
  default = false
}

variable "visibility_timeout" {
  type    = number
  default = 30
}

variable "sns_alarms_topic_arn" {
  type        = string
  default     = ""
  description = "SNS topic ARN for CloudWatch alarms on DLQ depth. Empty string disables alarms."
}

variable "message_retention_seconds" {
  type    = number
  default = 1209600
}
