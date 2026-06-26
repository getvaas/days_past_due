variable "lambda_role_name" {
  type = string
}

variable "lambda_policy_name" {
  type = string
}

variable "lambda_policy_actions" {
  type    = list(string)
  default = []
}

variable "lambda_policy_statements" {
  type = list(object({
    Effect   = string
    Action   = list(string)
    Resource = any
  }))
  default = []
}

variable "attach_basic_execution" {
  type        = bool
  default     = true
  description = "Attach AWSLambdaBasicExecutionRole managed policy."
}

variable "attach_vpc_access" {
  type        = bool
  default     = false
  description = "Attach AWSLambdaVPCAccessExecutionRole managed policy."
}
