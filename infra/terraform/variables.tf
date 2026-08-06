variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "environment" {
  type    = string
  default = "production"
}
variable "project_name" {
  type    = string
  default = "frontierops"
}
variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}
variable "container_image" {
  type        = string
  description = "Immutable ECR image URI including digest or tag"
}
variable "desired_count" {
  type    = number
  default = 2
}
variable "task_cpu" {
  type    = number
  default = 512
}
variable "task_memory" {
  type    = number
  default = 1024
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
variable "db_allocated_storage" {
  type    = number
  default = 20
}
variable "certificate_arn" {
  type     = string
  default  = null
  nullable = true
}
variable "allowed_ingress_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "servicenow_enabled" {
  type    = bool
  default = false
}
