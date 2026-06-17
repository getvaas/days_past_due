output "secret_arn" {
  value = data.aws_secretsmanager_secret.secret.arn
}

output "secret_name" {
  value = data.aws_secretsmanager_secret.secret.name
}

# Mapa con todas las claves del JSON del secret (ej. DATASOURCE___PAYMENTS_DB___URL).
output "values" {
  value     = jsondecode(data.aws_secretsmanager_secret_version.current.secret_string)
  sensitive = true
}
