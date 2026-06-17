output "queue_name" {
  value = aws_sqs_queue.queue.name
}

output "queue_arn" {
  value = aws_sqs_queue.queue.arn
}

output "queue_url" {
  value = aws_sqs_queue.queue.url
}

output "dead_letter_queue_arn" {
  value = one(aws_sqs_queue.dead_letter_queue[*].arn)
}
