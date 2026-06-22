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
