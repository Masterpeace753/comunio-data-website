resource "random_password" "db" {
  count = var.create_database && var.db_master_password == null ? 1 : 0

  length           = 24
  special          = true
  override_special = "_-=%+"
}

locals {
  db_master_password_value = coalesce(var.db_master_password, try(random_password.db[0].result, null))
}

resource "aws_security_group" "rds" {
  count = var.create_database ? 1 : 0

  name        = "${local.name_prefix}-rds"
  description = "Security group for the Comunio PostgreSQL instance"
  vpc_id      = local.vpc_id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds" })
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  count = var.create_database ? 1 : 0

  security_group_id            = aws_security_group.rds[0].id
  referenced_security_group_id = local.runtime_primary_security_group_id
  from_port                    = var.db_port
  to_port                      = var.db_port
  ip_protocol                  = "tcp"
}

resource "aws_db_subnet_group" "main" {
  count = var.create_database ? 1 : 0

  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = local.private_subnet_ids

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-db-subnets" })
}

resource "aws_db_instance" "main" {
  count = var.create_database ? 1 : 0

  identifier                  = "${local.name_prefix}-postgres"
  engine                      = "postgres"
  engine_version              = var.db_engine_version
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  max_allocated_storage       = var.db_max_allocated_storage
  db_name                     = var.db_name
  username                    = var.db_master_username
  password                    = local.db_master_password_value
  port                        = var.db_port
  db_subnet_group_name        = aws_db_subnet_group.main[0].name
  vpc_security_group_ids      = [aws_security_group.rds[0].id]
  multi_az                    = var.db_multi_az
  publicly_accessible         = false
  storage_encrypted           = true
  backup_retention_period     = var.db_backup_retention_days
  deletion_protection         = var.db_deletion_protection
  skip_final_snapshot         = var.db_skip_final_snapshot
  apply_immediately           = var.db_apply_immediately
  auto_minor_version_upgrade  = true
  performance_insights_enabled = var.db_enable_performance_insights

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })
}

resource "aws_secretsmanager_secret" "database_url" {
  count = var.create_database && var.database_url_secret_arn == null ? 1 : 0

  name = "${local.name_prefix}/database-url"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  count = var.create_database && var.database_url_secret_arn == null ? 1 : 0

  secret_id = aws_secretsmanager_secret.database_url[0].id
  secret_string = format(
    "postgresql://%s:%s@%s:%d/%s?sslmode=require",
    urlencode(var.db_master_username),
    urlencode(local.db_master_password_value),
    aws_db_instance.main[0].address,
    var.db_port,
    var.db_name,
  )
}