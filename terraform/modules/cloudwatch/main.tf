locals {
  retention_in_days = var.retention_in_days == null ? (contains(["prod", "mx"], var.environment) ? 30 : 7) : var.retention_in_days
}

resource "aws_cloudwatch_log_group" "cloudwatch_log_group" {
  name              = var.log_group_name
  retention_in_days = local.retention_in_days
}

resource "aws_cloudwatch_log_stream" "ecs_log_stream" {
  count          = var.log_stream_name != null ? 1 : 0
  name           = var.log_stream_name
  log_group_name = aws_cloudwatch_log_group.cloudwatch_log_group.name
}
