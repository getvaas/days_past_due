locals {
  # Alarmas activas solo si hay topic de alarmas configurado.
  activate_alarm = var.sns_alarms_topic_arn != "" ? 1 : 0

  # Las colas FIFO requieren sufijo .fifo
  queue_name    = var.fifo_queue ? "${var.name}_fifo_queue.fifo" : "${var.name}_standard_queue"
  dl_queue_name = var.fifo_queue ? "${var.name}_fifo_dead_letter_queue.fifo" : "${var.name}_standard_dead_letter_queue"
}
