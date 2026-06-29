output "job_queue_arn" {
  value       = aws_batch_job_queue.this.arn
  description = "ARN de la job queue de AWS Batch."
}

output "job_queue_name" {
  value       = aws_batch_job_queue.this.name
  description = "Nombre de la job queue."
}

output "job_definition_arn" {
  value       = aws_batch_job_definition.this.arn
  description = "ARN de la job definition (incluye revisión)."
}

output "job_definition_name" {
  value       = aws_batch_job_definition.this.name
  description = "Nombre de la job definition."
}

output "compute_environment_arn" {
  value       = aws_batch_compute_environment.this.arn
  description = "ARN del compute environment."
}
output "job_role_arn" {
  value = aws_iam_role.job_role.arn
}

output "job_role_name" {
  value = aws_iam_role.job_role.name
}

output "execution_role_arn" {
  value = aws_iam_role.execution_role.arn
}

output "execution_role_name" {
  value = aws_iam_role.execution_role.name
}

output "cloudwatch_log_group_name" {
  value       = aws_cloudwatch_log_group.this.name
  description = "Nombre del log group de CloudWatch del job."
}

output "cloudwatch_log_group_arn" {
  value       = aws_cloudwatch_log_group.this.arn
  description = "ARN del log group de CloudWatch del job."
}
