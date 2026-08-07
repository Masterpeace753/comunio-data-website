data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  effective_availability_zones = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  count = var.create_network ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "main" {
  count = var.create_network ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  count = var.create_network ? length(var.public_subnet_cidrs) : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.effective_availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-${count.index + 1}" })
}

resource "aws_subnet" "private" {
  count = var.create_network ? length(var.private_subnet_cidrs) : 0

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = local.effective_availability_zones[count.index]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-${count.index + 1}" })
}

resource "aws_route_table" "public" {
  count = var.create_network ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-rt" })
}

resource "aws_route_table" "private" {
  count = var.create_network ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-rt" })
}

resource "aws_route_table_association" "public" {
  count = var.create_network ? length(aws_subnet.public) : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count = var.create_network ? length(aws_subnet.private) : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_security_group" "ecs" {
  count = local.vpc_id != null && length(var.security_group_ids) == 0 ? 1 : 0

  name        = "${local.name_prefix}-ecs"
  description = "Security group for scheduled backend ingest tasks"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs" })
}

resource "aws_security_group" "secretsmanager_endpoint" {
  count = var.create_network ? 1 : 0

  name        = "${local.name_prefix}-secretsmanager-endpoint"
  description = "Allow ECS tasks to reach Secrets Manager through a VPC endpoint"
  vpc_id      = local.vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [local.runtime_primary_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-secretsmanager-endpoint" })
}

resource "aws_vpc_endpoint" "secretsmanager" {
  count = var.create_network ? 1 : 0

  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.secretsmanager_endpoint[0].id]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-secretsmanager-endpoint" })
}