resource "aws_ecs_cluster" "this" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
resource "aws_elasticache_subnet_group" "this" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = substr(local.name, 0, 40)
  description                = "FrontierOps durable evaluation queue"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 1
  port                       = 6379
  engine                     = "redis"
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.redis.id]
}
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name = "api", image = var.container_image, essential = true,
    portMappings = [{
      containerPort = 8000, protocol = "tcp"
    }],
    environment = [
      {
        name = "FRONTIEROPS_ENVIRONMENT", value = var.environment
      },
      {
        name = "FRONTIEROPS_AWS_REGION", value = var.aws_region
      },
      {
        name = "FRONTIEROPS_S3_REPORTS_BUCKET", value = aws_s3_bucket.reports.bucket
      },
      {
        name = "FRONTIEROPS_CLOUDWATCH_METRICS_ENABLED", value = "true"
      },
      {
        name = "FRONTIEROPS_REDIS_URL", value = "rediss://${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0"
      },
      {
        name = "SERVICENOW_ENABLED", value = tostring(var.servicenow_enabled)
      }
    ],
    secrets = concat(
      [{
        name = "FRONTIEROPS_DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.database.arn}:database_url::"
      }],
      var.servicenow_enabled ? [
        {
          name = "SERVICENOW_INSTANCE_URL", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:instance_url::"
        },
        {
          name = "SERVICENOW_USERNAME", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:username::"
        },
        {
          name = "SERVICENOW_PASSWORD", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:password::"
        }
      ] : []
    ),
    logConfiguration = {
      logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.api.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "api"
      }
    },
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/ready')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30

    }

    }, {
    name    = "worker", image = var.container_image, essential = true,
    command = ["python", "-m", "worker"],
    environment = [
      {
        name = "FRONTIEROPS_ENVIRONMENT", value = var.environment
      },
      {
        name = "FRONTIEROPS_AWS_REGION", value = var.aws_region
      },
      {
        name = "FRONTIEROPS_REDIS_URL", value = "rediss://${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0"
      },
      {
        name = "FRONTIEROPS_S3_REPORTS_BUCKET", value = aws_s3_bucket.reports.bucket
      },
      {
        name = "FRONTIEROPS_CLOUDWATCH_METRICS_ENABLED", value = "true"
      },
      {
        name = "SERVICENOW_ENABLED", value = tostring(var.servicenow_enabled)
      }
    ],
    secrets = concat(
      [{
        name = "FRONTIEROPS_DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.database.arn}:database_url::"
      }],
      var.servicenow_enabled ? [
        {
          name = "SERVICENOW_INSTANCE_URL", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:instance_url::"
        },
        {
          name = "SERVICENOW_USERNAME", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:username::"
        },
        {
          name = "SERVICENOW_PASSWORD", valueFrom = "${aws_secretsmanager_secret.servicenow.arn}:password::"
        }
      ] : []
    ),
    logConfiguration = {
      logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.api.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "worker"
      }
    }

  }])
}
resource "aws_ecs_service" "api" {
  name                   = "api"
  cluster                = aws_ecs_cluster.this.id
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = false
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [aws_lb_listener.api]
}
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 6
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
