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

output "log_group_name" {
  value       = module.cloudwatch.cloudwatch_log_group_name
  description = "Log group de CloudWatch donde escribirá la Lambda."
}

output "log_group_arn" {
  value       = module.cloudwatch.cloudwatch_log_group_arn
  description = "ARN del log group de la Lambda."
}
