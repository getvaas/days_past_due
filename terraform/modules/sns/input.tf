variable "environment" {
  type = string
}

variable "name" {
  type = string
}

variable "fifo_topic" {
  type    = bool
  default = false
}

variable "content_based_deduplication" {
  type    = bool
  default = false
}
