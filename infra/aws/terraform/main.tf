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
  vpc_id                         = coalesce(var.vpc_id, try(aws_vpc.main[0].id, null))
  public_subnet_ids              = length(var.public_subnet_ids) > 0 ? var.public_subnet_ids : [for subnet in aws_subnet.public : subnet.id]
  private_subnet_ids             = length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : [for subnet in aws_subnet.private : subnet.id]
  runtime_subnet_ids             = length(var.subnet_ids) > 0 ? var.subnet_ids : (var.assign_public_ip ? local.public_subnet_ids : local.private_subnet_ids)
  runtime_security_group_ids     = length(var.security_group_ids) > 0 ? var.security_group_ids : compact([try(aws_security_group.ecs[0].id, null)])
  runtime_primary_security_group_id = length(var.security_group_ids) > 0 ? var.security_group_ids[0] : try(aws_security_group.ecs[0].id, null)
  resolved_database_url_secret_arn = coalesce(var.database_url_secret_arn, try(aws_secretsmanager_secret.database_url[0].arn, null))
  use_live_comunio_secret        = var.comunio_snapshot_file == null && var.comunio_credentials_secret_arn != null
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
  image_tag_mutability = "MUTABLE"

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
  count = local.resolved_database_url_secret_arn == null ? 0 : 1

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [local.resolved_database_url_secret_arn]
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

  container_definitions = jsonencode([
    {
      name      = "ingest-runner"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true
      command   = ["python", "-m", "src.ingest.runner", "--run-type", "manual", "--mode", "snapshot"]
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

  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.ingest.arn
    platform_version    = "LATEST"

    network_configuration {
      subnets          = local.runtime_subnet_ids
      security_groups  = local.runtime_security_group_ids
      assign_public_ip = var.assign_public_ip
    }
  }
}