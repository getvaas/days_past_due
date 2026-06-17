variable "cloudwatch_configuration" {
  type = object({
    log_group_name    = string
    retention_in_days = number
  })
}
