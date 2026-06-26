variable "iam_configuration" {
  type = object({
    role_lambda_name      = string
    policy_lambda_name    = string
    policy_lambda_actions = list(string)
  })
}
