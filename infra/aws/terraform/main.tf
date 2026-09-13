terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags,
  )
  vpc_id                            = coalesce(var.vpc_id, try(aws_vpc.main[0].id, null))
  public_subnet_ids                 = length(var.public_subnet_ids) > 0 ? var.public_subnet_ids : [for subnet in aws_subnet.public : subnet.id]
  private_subnet_ids                = length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : [for subnet in aws_subnet.private : subnet.id]
  runtime_subnet_ids                = length(var.subnet_ids) > 0 ? var.subnet_ids : (var.assign_public_ip ? local.public_subnet_ids : local.private_subnet_ids)
  runtime_security_group_ids        = length(var.security_group_ids) > 0 ? var.security_group_ids : compact([try(aws_security_group.ecs[0].id, null)])
  runtime_primary_security_group_id = length(var.security_group_ids) > 0 ? var.security_group_ids[0] : try(aws_security_group.ecs[0].id, null)
  resolved_database_url_secret_arn  = coalesce(var.database_url_secret_arn, try(aws_secretsmanager_secret.database_url[0].arn, null))
  use_live_comunio_secret           = var.comunio_snapshot_file == null && var.comunio_credentials_secret_arn != null
  api_runtime_subnet_ids            = local.public_subnet_ids
  task_environment = concat(
    [
      {
        name  = "APP_ENV"
        value = "production"
      },
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "COMUNIO_REQUIRE_SECRET_MODE"
        value = local.use_live_comunio_secret ? "true" : "false"
      },
      {
        name  = "COMUNIO_LOGIN_RETRY_ATTEMPTS"
        value = tostring(var.login_retry_attempts)
      },
      {
        name  = "COMUNIO_LOGIN_RETRY_WAIT_SECONDS"
        value = tostring(var.login_retry_wait_seconds)
      }
    ],
    var.comunio_snapshot_file != null ? [
      {
        name  = "COMUNIO_SNAPSHOT_FILE"
        value = var.comunio_snapshot_file
      }
    ] : [],
    local.use_live_comunio_secret ? [
      {
        name  = "COMUNIO_SECRET_NAME"
        value = var.comunio_credentials_secret_arn
      }
    ] : []
  )
}

resource "aws_ecr_repository" "backend" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${local.name_prefix}-ingest"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

data "aws_iam_policy_document" "ecs_task_execution_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name_prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "execution_secrets" {
  count = local.resolved_database_url_secret_arn != null || (var.api_enabled && var.api_database_url_secret_arn != null) ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = compact([local.resolved_database_url_secret_arn, var.api_enabled ? var.api_database_url_secret_arn : null])
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  count = local.resolved_database_url_secret_arn == null ? 0 : 1

  name   = "${local.name_prefix}-execution-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets[0].json
}

resource "aws_iam_role" "task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "task_secrets" {
  count = local.use_live_comunio_secret ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.comunio_credentials_secret_arn]
  }
}

resource "aws_iam_role_policy" "task_secrets" {
  count = local.use_live_comunio_secret ? 1 : 0

  name   = "${local.name_prefix}-task-secrets"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_secrets[0].json
}

resource "aws_ecs_cluster" "backend" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "ingest" {
  family                   = "${local.name_prefix}-ingest"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.task_cpu)
  memory                   = tostring(var.task_memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  lifecycle {
    precondition {
      condition     = !(var.environment == "prod" || var.environment == "production") || var.comunio_credentials_secret_arn != null
      error_message = "Production deployments require a Secrets Manager ARN for the Comunio credentials and forbid ENV-only credential usage."
    }

    precondition {
      condition     = var.assign_public_ip || !var.create_network || var.enable_nat_gateway || var.enable_nat_instance
      error_message = "Private tasks in a Terraform-managed VPC require a NAT gateway or NAT instance for outbound Comunio and AWS access."
    }
  }

  container_definitions = jsonencode([
    {
      name        = "ingest-runner"
      image       = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential   = true
      command     = ["python", "-m", "src.ingest.runner", "--run-type", "scheduled", "--mode", "snapshot"]
      environment = local.task_environment
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = local.resolved_database_url_secret_arn
        },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.api_enabled ? 1 : 0
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_iam_role" "api_task" {
  count              = var.api_enabled ? 1 : 0
  name               = "${local.name_prefix}-api-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
  tags               = local.common_tags
}

resource "aws_ecs_task_definition" "api" {
  count                    = var.api_enabled ? 1 : 0
  family                   = "${local.name_prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.api_cpu)
  memory                   = tostring(var.api_memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api_task[0].arn

  lifecycle {
    precondition {
      condition     = var.api_database_url_secret_arn != null
      error_message = "The public API requires a separate read-only DATABASE_URL Secrets Manager ARN."
    }

    precondition {
      condition     = length(local.api_runtime_subnet_ids) >= 2
      error_message = "The public API ALB requires at least two public subnets in different availability zones."
    }
  }

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.api_image_tag}"
      essential = true
      environment = [
        {
          name  = "APP_ENV"
          value = "production"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "API_ALLOWED_ORIGINS"
          value = var.api_allowed_origins
        },
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = var.api_database_url_secret_arn
        },
      ]
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        },
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    },
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  tags = local.common_tags
}

resource "aws_iam_role" "api_bootstrap" {
  count              = var.api_enabled ? 1 : 0
  name               = "${local.name_prefix}-api-bootstrap"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "api_bootstrap_secrets" {
  count = var.api_enabled ? 1 : 0

  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = compact([
      local.resolved_database_url_secret_arn,
      var.api_database_url_secret_arn,
    ])
  }

  statement {
    actions   = ["secretsmanager:PutSecretValue"]
    resources = [var.api_database_url_secret_arn]
  }
}

resource "aws_iam_role_policy" "api_bootstrap_secrets" {
  count  = var.api_enabled ? 1 : 0
  name   = "${local.name_prefix}-api-bootstrap-secrets"
  role   = aws_iam_role.api_bootstrap[0].id
  policy = data.aws_iam_policy_document.api_bootstrap_secrets[0].json
}

resource "aws_ecs_task_definition" "api_bootstrap" {
  count                    = var.api_enabled ? 1 : 0
  family                   = "${local.name_prefix}-api-bootstrap"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.api_cpu)
  memory                   = tostring(var.api_memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api_bootstrap[0].arn

  container_definitions = jsonencode([
    {
      name      = "api-bootstrap"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.api_image_tag}"
      essential = true
      command   = ["python", "-m", "src.ops.provision_api_readonly_user"]
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "MASTER_DATABASE_URL_SECRET_ARN"
          value = local.resolved_database_url_secret_arn
        },
        {
          name  = "API_DATABASE_URL_SECRET_ARN"
          value = var.api_database_url_secret_arn
        },
        {
          name  = "API_DATABASE_ROLE"
          value = "comunio_api_readonly"
        },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "bootstrap"
        }
      }
    },
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  lifecycle {
    precondition {
      condition     = var.api_database_url_secret_arn != null
      error_message = "The API bootstrap task requires the API Secrets Manager ARN."
    }
  }

  tags = local.common_tags
}

resource "aws_lb" "api" {
  count              = var.api_enabled ? 1 : 0
  name               = "${local.name_prefix}-api"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.api_alb[0].id]
  subnets            = local.api_runtime_subnet_ids

  tags = local.common_tags
}

resource "aws_lb_target_group" "api" {
  count       = var.api_enabled ? 1 : 0
  name        = "${local.name_prefix}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id

  health_check {
    enabled             = true
    path                = "/health/ready"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "api_http" {
  count             = var.api_enabled ? 1 : 0
  load_balancer_arn = aws_lb.api[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }
}

resource "aws_ecs_service" "api" {
  count                              = var.api_enabled ? 1 : 0
  name                               = "${local.name_prefix}-api"
  cluster                            = aws_ecs_cluster.backend.id
  task_definition                    = aws_ecs_task_definition.api[0].arn
  desired_count                      = var.api_desired_count
  launch_type                        = "FARGATE"
  platform_version                   = var.ecs_platform_version
  health_check_grace_period_seconds  = 60
  enable_ecs_managed_tags            = true
  propagate_tags                     = "SERVICE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = local.api_runtime_subnet_ids
    security_groups  = [aws_security_group.api[0].id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api[0].arn
    container_name   = "api"
    container_port    = 8000
  }

  depends_on = [aws_lb_listener.api_http]

  tags = local.common_tags
}

data "aws_iam_policy_document" "events_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "events" {
  name               = "${local.name_prefix}-events"
  assume_role_policy = data.aws_iam_policy_document.events_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "events_run_task" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.ingest.arn]
  }

  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn, aws_iam_role.task.arn]
  }
}

resource "aws_iam_role_policy" "events_run_task" {
  name   = "${local.name_prefix}-events-run-task"
  role   = aws_iam_role.events.id
  policy = data.aws_iam_policy_document.events_run_task.json
}

resource "aws_sqs_queue" "scheduler_dlq" {
  name                      = "${local.name_prefix}-scheduler-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = local.common_tags
}

data "aws_iam_policy_document" "events_dlq" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scheduler_dlq.arn]
  }
}

resource "aws_iam_role_policy" "events_dlq" {
  name   = "${local.name_prefix}-events-dlq"
  role   = aws_iam_role.events.id
  policy = data.aws_iam_policy_document.events_dlq.json
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${local.name_prefix}-snapshot-schedule"
  description         = "Triggers the Comunio backend ingest snapshot task"
  schedule_expression = var.schedule_expression
  state               = var.enable_schedule ? "ENABLED" : "DISABLED"

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "ecs" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "${local.name_prefix}-ingest"
  arn       = aws_ecs_cluster.backend.arn
  role_arn  = aws_iam_role.events.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 2
  }

  dead_letter_config {
    arn = aws_sqs_queue.scheduler_dlq.arn
  }

  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.ingest.arn
    platform_version    = var.ecs_platform_version

    network_configuration {
      subnets          = local.runtime_subnet_ids
      security_groups  = local.runtime_security_group_ids
      assign_public_ip = var.assign_public_ip
    }
  }
}

# AP-9.2: automated check whether a scheduled run finished successfully or
# was aborted after exhausting login retries, so operators are notified
# without needing to poll ECS/CloudWatch manually.
resource "aws_cloudwatch_log_metric_filter" "login_exhausted" {
  name           = "${local.name_prefix}-login-retries-exhausted"
  log_group_name = aws_cloudwatch_log_group.backend.name
  pattern        = "\"event=run_failed\" \"stage=login\""

  metric_transformation {
    name      = "LoginRetriesExhausted"
    namespace = "Comunio/Ingest"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "login_exhausted" {
  alarm_name          = "${local.name_prefix}-login-retries-exhausted"
  alarm_description   = "Scheduled ingest run failed after exhausting all login retries"
  namespace           = aws_cloudwatch_log_metric_filter.login_exhausted.metric_transformation[0].namespace
  metric_name         = aws_cloudwatch_log_metric_filter.login_exhausted.metric_transformation[0].name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = compact([var.alert_sns_topic_arn])
  ok_actions          = compact([var.alert_sns_topic_arn])

  tags = local.common_tags
}