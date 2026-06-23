variable "environment" {
  type = string
}

variable "name" {
  type        = string
  description = "Nombre base del recurso (ej. dev-days-past-due-batch)."
}

variable "ecr_image_uri" {
  type        = string
  description = "URI completo de la imagen Docker en ECR (incluyendo tag)."
}

variable "job_role_arn" {
  type        = string
  description = "ARN del rol IAM que asume el contenedor del job (acceso a S3, SNS, Secrets)."
}

variable "execution_role_arn" {
  type        = string
  description = "ARN del rol IAM de ejecución ECS (pull de ECR, escritura en CloudWatch)."
}

variable "cloudwatch_log_group" {
  type        = string
  description = "Nombre del log group de CloudWatch donde el job escribe logs."
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "max_vcpus" {
  type        = number
  default     = 16
  description = "Máximo de vCPUs del compute environment."
}

variable "job_vcpus" {
  type        = string
  default     = "1"
  description = "vCPUs asignadas al job (formato string, ej. '1', '2')."
}

variable "job_memory" {
  type        = number
  default     = 2048
  description = "Memoria en MB asignada al job."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets privadas donde corre el compute environment."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups asignados al compute environment."
}

variable "environment_variables" {
  type        = map(string)
  default     = {}
  description = "Variables de entorno inyectadas en el contenedor del job."
}
