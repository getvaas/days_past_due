variable "lambda_function_name" {
  type = string
}

variable "sqs_queue_arn" {
  type = string
}

variable "batch_size" {
  type    = number
  default = 1
}

variable "maximum_batching_window_in_seconds" {
  type    = number
  default = 0
}
