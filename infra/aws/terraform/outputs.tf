output "ecr_repository_url" {
  description = "ECR repository URL for docker push"
  value       = aws_ecr_repository.backend.repository_url
}

output "vpc_id" {
  description = "Managed or reused VPC ID used by the workload"
  value       = local.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs available to ECS when assign_public_ip is true"
  value       = local.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs used by RDS and optionally ECS"
  value       = local.private_subnet_ids
}

output "runtime_subnet_ids" {
  description = "Subnet IDs effectively used by the ECS ingest task"
  value       = local.runtime_subnet_ids
}

output "ecs_security_group_ids" {
  description = "Security groups attached to the ECS ingest task"
  value       = local.runtime_security_group_ids
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.backend.name
}

output "ecs_task_definition_arn" {
  description = "Task definition ARN for manual runs and overrides"
  value       = aws_ecs_task_definition.ingest.arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name used by the ingest task"
  value       = aws_cloudwatch_log_group.backend.name
}

output "database_url_secret_arn" {
  description = "Secret ARN used for DATABASE_URL injection"
  value       = local.resolved_database_url_secret_arn
}

output "rds_endpoint" {
  description = "Endpoint of the managed PostgreSQL instance, if created"
  value       = try(aws_db_instance.main[0].address, null)
}

output "rds_security_group_id" {
  description = "Security group ID of the managed PostgreSQL instance, if created"
  value       = try(aws_security_group.rds[0].id, null)
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name for the scheduled ingest run"
  value       = aws_cloudwatch_event_rule.schedule.name
}

output "scheduler_dlq_url" {
  description = "URL of the EventBridge scheduler dead-letter queue"
  value       = aws_sqs_queue.scheduler_dlq.url
}

output "login_retries_exhausted_alarm_name" {
  description = "CloudWatch alarm name that fires when a scheduled run exhausts all login retries"
  value       = aws_cloudwatch_metric_alarm.login_exhausted.alarm_name
}

output "api_alb_dns_name" {
  description = "Public DNS name of the API Application Load Balancer"
  value       = try(aws_lb.api[0].dns_name, null)
}

output "api_service_name" {
  description = "ECS service name for the public API"
  value       = try(aws_ecs_service.api[0].name, null)
}

output "api_task_definition_arn" {
  description = "Task definition ARN for the public API"
  value       = try(aws_ecs_task_definition.api[0].arn, null)
}