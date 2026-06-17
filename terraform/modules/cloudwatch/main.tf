# Log group de CloudWatch donde la Lambda escribe sus logs.
# El nombre debe ser /aws/lambda/<nombre-exacto-de-la-funcion> para que Lambda lo use.

resource "aws_cloudwatch_log_group" "log_group" {
  name              = var.cloudwatch_configuration.log_group_name
  retention_in_days = var.cloudwatch_configuration.retention_in_days
}
