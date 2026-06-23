output "job_role_arn" {
  value       = aws_iam_role.job_role.arn
  description = "ARN del rol del contenedor del job."
}

output "execution_role_arn" {
  value       = aws_iam_role.execution_role.arn
  description = "ARN del rol de ejecución ECS."
}
