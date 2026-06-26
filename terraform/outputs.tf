output "queue_name" {
  value       = module.sqs.queue_name
  description = "Nombre de la cola FIFO de entrada."
}

output "queue_arn" {
  value       = module.sqs.queue_arn
  description = "ARN de la cola. El rol de la Lambda necesita sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes sobre este ARN."
}

output "queue_url" {
  value       = module.sqs.queue_url
  description = "URL de la cola (para receive-message / send-message)."
}

output "dead_letter_queue_arn" {
  value       = module.sqs.dead_letter_queue_arn
  description = "ARN de la DLQ."
}

output "inbound_topic_arn" {
  value       = local.inbound_topic_arn
  description = "ARN del topic SNS de entrada (creado acá o el del Enricher)."
}

output "s3_loan_tape_bucket_name" {
  value       = module.s3_loan_tape.bucket_name
  description = "Nombre del bucket S3 donde la Lambda lee y escribe los loan tapes."
}

output "s3_loan_tape_bucket_arn" {
  value       = module.s3_loan_tape.bucket_arn
  description = "ARN del bucket. Necesario para la policy IAM del rol Lambda."
}

output "log_group_name" {
  value       = module.cloudwatch.cloudwatch_log_group_name
  description = "Log group de CloudWatch donde escribirá la Lambda."
}

output "log_group_arn" {
  value       = module.cloudwatch.cloudwatch_log_group_arn
  description = "ARN del log group de la Lambda."
}

output "lambda_function_name" {
  value       = module.lambda_dpd.lambda_function_name
  description = "Nombre de la función Lambda DPD desplegada."
}

output "lambda_function_arn" {
  value       = module.lambda_dpd.lambda_function_arn
  description = "ARN de la Lambda DPD."
}

output "iam_role_lambda_arn" {
  value       = module.iam_lambda_dpd.iam_role_lambda_arn
  description = "ARN del rol IAM asignado a la Lambda."
}

output "batch_job_queue_arn" {
  value       = module.batch_dpd.job_queue_arn
  description = "ARN de la job queue de AWS Batch."
}

output "batch_job_definition_arn" {
  value       = module.batch_dpd.job_definition_arn
  description = "ARN de la job definition de AWS Batch."
}

output "ecr_repository_uri" {
  value       = module.ecr_dpd.ecr_repository_uri
  description = "URI del repositorio ECR compartido por Lambda y Batch."
}

output "response_sns_topic_arn" {
  value       = module.sns_response.sns_topic_arn
  description = "ARN del topic SNS donde Lambda/Batch publican el resultado del cálculo DPD."
}

output "response_queue_arn" {
  value       = module.sqs_response.queue_arn
  description = "ARN de la cola SQS donde el downstream consume los resultados DPD."
}

output "response_queue_url" {
  value       = module.sqs_response.queue_url
  description = "URL de la cola SQS de respuesta."
}
