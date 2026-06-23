variable "job_role_name" {
  type        = string
  description = "Nombre del rol IAM del contenedor del job."
}

variable "job_policy_name" {
  type        = string
  description = "Nombre de la policy IAM del job."
}

variable "job_policy_actions" {
  type        = list(string)
  description = "Acciones IAM permitidas al contenedor del job."
}

variable "execution_role_name" {
  type        = string
  description = "Nombre del rol de ejecución ECS (pull ECR + CloudWatch)."
}
