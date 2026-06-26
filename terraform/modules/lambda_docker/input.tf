variable "name" {
  type = string
}

variable "memory_size" {
  type    = number
  default = 256
}

variable "timeout" {
  type    = number
  default = 60
}

variable "iam_role_lambda_arn" {
  type = string
}

variable "ecr_repository_uri" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "environment_variables" {
  type = map(any)
}

variable "reserved_concurrent_executions" {
  type    = number
  default = -1
}

variable "ephemeral_storage" {
  type    = number
  default = 512
}
