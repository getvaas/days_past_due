output "ecr_repository_uri" {
  value = aws_ecr_repository.repository.repository_url
}

output "ecr_repository_arn" {
  value = aws_ecr_repository.repository.arn
}
