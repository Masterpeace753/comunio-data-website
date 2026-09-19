variable "aws_region" {
  description = "AWS region for the deployment"
  type        = string
}

variable "create_network" {
  description = "Create a dedicated VPC with public and private subnets"
  type        = bool
  default     = false
}

variable "enable_nat_gateway" {
  description = "Create a managed NAT Gateway in a public subnet for private subnet egress (Option A)"
  type        = bool
  default     = false
}

variable "enable_nat_instance" {
  description = "Create a low-cost t4g.nano NAT Instance in a public subnet for private subnet egress (Option B)"
  type        = bool
  default     = false

  validation {
    condition     = !var.enable_nat_instance || !var.enable_nat_gateway
    error_message = "enable_nat_gateway and enable_nat_instance are mutually exclusive."
  }
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
  description = "Immutable ECR image tag or commit SHA that ECS should run"
  type        = string
  default     = "release-immutable"

  validation {
    condition     = trimspace(var.image_tag) != "" && var.image_tag != "latest" && var.image_tag != "latest:latest"
    error_message = "image_tag must be a non-empty immutable tag or commit SHA and must not use 'latest'."
  }
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
  default     = "cron(0 6 * * ? *)"
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

variable "api_database_url_secret_arn" {
  description = "Secrets Manager ARN containing the API read-only DATABASE_URL; used by the future public API service, never by ingest"
  type        = string
  default     = null
}

variable "api_enabled" {
  description = "Deploy the public read-only FastAPI ECS service and ALB"
  type        = bool
  default     = false
}

variable "api_image_tag" {
  description = "Immutable ECR image tag for the API service"
  type        = string
  default     = "v0.5.0"

  validation {
    condition     = trimspace(var.api_image_tag) != "" && var.api_image_tag != "latest" && var.api_image_tag != "latest:latest"
    error_message = "api_image_tag must be a non-empty immutable tag and must not use 'latest'."
  }
}

variable "api_cpu" {
  description = "Fargate CPU units for the API service"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Fargate memory in MiB for the API service"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired API task count for the cost-optimized MVP"
  type        = number
  default     = 1
}

variable "api_allowed_origins" {
  description = "Comma-separated browser origins allowed by the API CORS policy"
  type        = string
  default     = "http://localhost:3000,http://127.0.0.1:3000"
}

variable "api_p95_threshold_seconds" {
  description = "ALB target response time P95 alarm threshold for the API"
  type        = number
  default     = 0.5
}

variable "api_5xx_rate_threshold_percent" {
  description = "ALB target 5xx error-rate alarm threshold for the API"
  type        = number
  default     = 5
}

variable "api_4xx_rate_threshold_percent" {
  description = "ALB target 4xx error-rate alarm threshold for the API"
  type        = number
  default     = 25
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

variable "ecs_platform_version" {
  description = "Pinned ECS Fargate platform version for scheduled runs"
  type        = string
  default     = "1.4.0"
}

variable "alert_sns_topic_arn" {
  description = "Optional existing SNS topic ARN for ingest failure alarms (e.g. login retries exhausted). No notification is sent if null."
  type        = string
  default     = null
}

variable "login_retry_attempts" {
  description = "Number of login attempts before a scheduled ingest run is marked failed"
  type        = number
  default     = 3
}

variable "login_retry_wait_seconds" {
  description = "Wait time in seconds between login retry attempts"
  type        = number
  default     = 300
}

