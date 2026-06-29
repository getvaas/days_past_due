#INPUTS
variable "environment" {
  type = string
}
variable "profile" {
  type = string
  default = ""
  description = "Aws cli profile"
}
variable "aws_region" {
  type = string
}
variable "project_name_camel_case" {
  type = string
}
variable "project_name_snake_case" {
  type = string
}
variable "author" {
  type = string
}
variable "subnet_private_ids" {
  type = list(string)
}
variable "security_group_id" {
  type = string
}
variable "environment_variables" {
  type = map(any)
}
variable "github_repository" {
  type = string
}
variable "ephemeral_storage" {
  type = string
  default = 1024
}
variable "input_sns" {
  type = string
  default = ""
}