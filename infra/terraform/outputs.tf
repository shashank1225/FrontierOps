output "alb_url" {
  value = "${var.certificate_arn == null ? "http" : "https"}://${aws_lb.api.dns_name}"
}
output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}
output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}
output "ecs_service_name" {
  value = aws_ecs_service.api.name
}
output "reports_bucket" {
  value = aws_s3_bucket.reports.bucket
}
output "servicenow_secret_arn" {
  value = aws_secretsmanager_secret.servicenow.arn
}
output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}
output "task_definition_arn" {
  value = aws_ecs_task_definition.api.arn
}
