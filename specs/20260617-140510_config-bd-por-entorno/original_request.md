# Original request

> si hay una ejecucuion local levanta la configuracion de la base desde el .env y si es por otro entorno hazlo mediante el secret_manager

## Aclaraciones (ronda de preguntas)

- **Detección de entorno**: por `AWS_LAMBDA_FUNCTION_NAME` — variable que AWS inyecta automáticamente en las
  Lambdas. Si existe → entorno desplegado (Secrets Manager); si no → local (`.env`).
- **Fuente del secret**: la app lee el secret en runtime con boto3 (`GetSecretValue`).
- **Mapeo**: se parsea `DATASOURCE___PAYMENTS_DB___URL` a host/puerto/base; `USERNAME`→user, `PASSWORD`→password.
- **Punto 5 (cacheo)**: el valor se obtiene vía el permiso `secretsmanager:GetSecretValue` del rol de ejecución.

## Contexto IAM provisto por el usuario

El rol de ejecución debe incluir, entre otras, la acción `secretsmanager:GetSecretValue` (junto con las de
SQS/SNS/S3/logs ya conocidas):

```hcl
iam_configuration = {
  ecs_policy = {
    name = "${local.name_kebab_case}-ecs-policy"
    role = "${local.name_kebab_case}-ecs-role"
    actions = [
      "ecr:GetAuthorizationToken", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload", "logs:CreateLogStream", "logs:PutLogEvents", "logs:CreateLogGroup",
      "secretsmanager:GetSecretValue",
      "s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject",
      "ssm:GetParametersByPath", "sns:ListTopics", "sns:Publish",
      "sqs:DeleteMessage", "sqs:ReceiveMessage"
    ]
  }
}
```
