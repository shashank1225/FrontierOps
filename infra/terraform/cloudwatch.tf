resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = var.log_retention_days
}
resource "aws_cloudwatch_metric_alarm" "blocked_releases" {
  alarm_name          = "${local.name}-blocked-releases"
  namespace           = "FrontierOps"
  metric_name         = "blocked_release_count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
}
