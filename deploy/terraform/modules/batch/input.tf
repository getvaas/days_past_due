variable "name" {
  type        = string
  description = "Nombre base del recurso (ej. dev-days-past-due-batch). Base para derivar los nombres de roles, policy, log group y demás recursos."
}

variable "environment" {
  type        = string
  description = "Environment (dev|stg|prod|mx). Usado para resolver subnets/security groups por defecto y la retención de logs."
}

variable "ecr_image_uri" {
  type        = string
  description = "URI completo de la imagen Docker en ECR (incluyendo tag)."
}

# Compute / job sizing
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

variable "architectures" {
  type        = list(string)
  default     = ["X86_64"]
  description = "Arquitectura de CPU del job. Fargate toma una sola (ej. [\"ARM64\"] o [\"X86_64\"])."
}

# Networking (opcional — si se omiten, se resuelven por environment)
variable "subnet_ids" {
  type        = list(string)
  default     = []
  description = "Subnets privadas donde corre el compute environment. Si está vacío, usa las subnets privadas por defecto de var.environment."
}

variable "security_group_ids" {
  type        = list(string)
  default     = []
  description = "Security groups del compute environment. Si está vacío, usa los security groups por defecto de var.environment."
}

variable "environment_variables" {
  type        = map(string)
  default     = {}
  description = "Variables de entorno inyectadas en el contenedor del job."
}

# IAM (opcional — nombres derivados de var.name si se omiten)
variable "job_role_name" {
  type        = string
  default     = null
  description = "Nombre del rol IAM del job. Default: <name>-job-role."
}

variable "job_policy_name" {
  type        = string
  default     = null
  description = "Nombre de la policy del job. Default: <name>-job-policy."
}

variable "job_policy_actions" {
  type        = list(string)
  default     = []
  description = "Acciones permitidas (sobre '*') para el rol del job (acceso a S3, SNS, Secrets, etc.)."
}

variable "execution_role_name" {
  type        = string
  default     = null
  description = "Nombre del rol de ejecución ECS. Default: <name>-execution-role."
}

# CloudWatch logs (opcional — derivado de var.name si se omite)
variable "cloudwatch_log_group_name" {
  type        = string
  default     = null
  description = "Nombre del log group de CloudWatch que crea el módulo. Default: /aws/batch/<name>."
}

variable "log_retention_in_days" {
  type        = number
  default     = null
  description = "Días de retención de los logs. Default: 30 en prod, 7 en el resto."
}
