variable "aws_region" {
  description = "AWS region for the deployment"
  type        = string
}

variable "create_network" {
  description = "Create a dedicated VPC with public and private subnets"
  type        = bool
  default     = false
}

variable "create_database" {
  description = "Create a managed PostgreSQL RDS instance and a DATABASE_URL secret"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "Existing VPC ID when reusing network infrastructure"
  type        = string
  default     = null
}

variable "vpc_cidr" {
  description = "CIDR range for a managed VPC"
  type        = string
  default     = "10.42.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used for managed subnets"
  type        = list(string)
  default     = []
}

variable "public_subnet_cidrs" {
  description = "CIDR ranges for managed public subnets"
  type        = list(string)
  default     = ["10.42.1.0/24", "10.42.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR ranges for managed private subnets"
  type        = list(string)
  default     = ["10.42.11.0/24", "10.42.12.0/24"]
}

variable "project_name" {
  description = "Project identifier used for naming"
  type        = string
  default     = "comunio"
}

variable "environment" {
  description = "Environment name used for naming and tags"
  type        = string
  default     = "prod"
}

variable "ecr_repository_name" {
  description = "ECR repository name for the backend image"
  type        = string
  default     = "comunio-backend-ingest"
}

variable "image_tag" {
  description = "ECR image tag that ECS should run"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 1024
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for the ingest task"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "enable_schedule" {
  description = "Whether the EventBridge schedule should be active"
  type        = bool
  default     = false
}

variable "enable_container_insights" {
  description = "Whether ECS container insights should be enabled"
  type        = bool
  default     = true
}

variable "assign_public_ip" {
  description = "Whether the scheduled Fargate task should get a public IP"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "subnet_ids" {
  description = "Subnets used by the Fargate task"
  type        = list(string)
  default     = []
}

variable "public_subnet_ids" {
  description = "Existing public subnets used when assign_public_ip is true"
  type        = list(string)
  default     = []
}

variable "private_subnet_ids" {
  description = "Existing private subnets used by RDS and optionally ECS"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security groups attached to the Fargate task"
  type        = list(string)
  default     = []
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN containing the full DATABASE_URL string"
  type        = string
  default     = null
}

variable "comunio_credentials_secret_arn" {
  description = "Secrets Manager ARN containing the Comunio username/password JSON"
  type        = string
  default     = null
}

variable "comunio_snapshot_file" {
  description = "Optional snapshot fixture path inside the container to bypass live Comunio login"
  type        = string
  default     = null
}

variable "db_name" {
  description = "Database name for a managed RDS instance"
  type        = string
  default     = "comunio"
}

variable "db_port" {
  description = "Database port for PostgreSQL"
  type        = number
  default     = 5432
}

variable "db_master_username" {
  description = "Master username for a managed RDS instance"
  type        = string
  default     = "comunio"
}

variable "db_master_password" {
  description = "Optional explicit master password for a managed RDS instance"
  type        = string
  default     = null
  sensitive   = true
}

variable "db_instance_class" {
  description = "Instance class for the managed RDS instance"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.14"
}

variable "db_allocated_storage" {
  description = "Initial storage size for the managed RDS instance in GiB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum autoscaled storage size for the managed RDS instance in GiB"
  type        = number
  default     = 100
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for the managed RDS instance"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "Backup retention in days for the managed RDS instance"
  type        = number
  default     = 7
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for the managed RDS instance"
  type        = bool
  default     = false
}

variable "db_skip_final_snapshot" {
  description = "Skip the final snapshot when destroying the managed RDS instance"
  type        = bool
  default     = true
}

variable "db_apply_immediately" {
  description = "Apply RDS changes immediately instead of during the next maintenance window"
  type        = bool
  default     = true
}

variable "db_enable_performance_insights" {
  description = "Enable Performance Insights for the managed RDS instance"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}