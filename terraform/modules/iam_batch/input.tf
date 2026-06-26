variable "job_role_name" {
  type = string
}

variable "job_policy_name" {
  type = string
}

variable "execution_role_name" {
  type = string
}

variable "job_policy_actions" {
  type    = list(string)
  default = []
}
