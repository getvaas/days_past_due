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
