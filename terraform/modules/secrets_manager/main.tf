# Lee un secret existente de AWS Secrets Manager y expone su contenido JSON.
# NO crea el secret: se asume que ya existe (lo gestiona el equipo de infra/Payments).

data "aws_secretsmanager_secret" "secret" {
  name = var.secret_name
}

data "aws_secretsmanager_secret_version" "current" {
  secret_id = data.aws_secretsmanager_secret.secret.id
}
