variable "log_group_name" {
  type = string
}

variable "log_stream_name" {
  type    = string
  default = null
}

variable "retention_in_days" {
  type    = string
  default = null
}

variable "environment" {
  type    = string
  default = null
}
