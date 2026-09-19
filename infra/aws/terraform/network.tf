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

# Option A: Managed NAT Gateway for private subnet outbound internet access
resource "aws_eip" "nat" {
  count = var.create_network && var.enable_nat_gateway ? 1 : 0

  domain = "vpc"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-nat-eip" })
}

resource "aws_nat_gateway" "main" {
  count = var.create_network && var.enable_nat_gateway ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-nat-gw" })

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route" "private_nat_gateway" {
  count = var.create_network && var.enable_nat_gateway ? 1 : 0

  route_table_id         = aws_route_table.private[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[0].id
}

# Option B: Low-cost t4g.nano NAT Instance for private subnet outbound internet access
data "aws_ami" "amazon_linux_2023_arm64" {
  count = var.create_network && var.enable_nat_instance && !var.enable_nat_gateway ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.1-arm64"]
  }
}

resource "aws_security_group" "nat_instance" {
  count = var.create_network && var.enable_nat_instance && !var.enable_nat_gateway ? 1 : 0

  name        = "${local.name_prefix}-nat-instance"
  description = "Security group for low-cost t4g.nano NAT instance"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-nat-instance-sg" })
}

resource "aws_instance" "nat" {
  count = var.create_network && var.enable_nat_instance && !var.enable_nat_gateway ? 1 : 0

  ami                         = data.aws_ami.amazon_linux_2023_arm64[0].id
  instance_type               = "t4g.nano"
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.nat_instance[0].id]
  associate_public_ip_address = true
  source_dest_check           = false

  user_data = <<-EOF
              #!/bin/bash
              sysctl -w net.ipv4.ip_forward=1
              echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
              iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
              dnf install -y iptables-services
              systemctl enable iptables
              service iptables save
              EOF

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-nat-instance" })
}

resource "aws_route" "private_nat_instance" {
  count = var.create_network && var.enable_nat_instance && !var.enable_nat_gateway ? 1 : 0

  route_table_id         = aws_route_table.private[0].id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = aws_instance.nat[0].primary_network_interface_id
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

resource "aws_security_group" "api_alb" {
  count = var.api_enabled ? 1 : 0

  name        = "${local.name_prefix}-api-alb"
  description = "Internal ALB for the read-only Comunio API"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api-alb" })
}

resource "aws_security_group" "api" {
  count = var.api_enabled ? 1 : 0

  name        = "${local.name_prefix}-api"
  description = "ECS security group for the read-only Comunio API"
  vpc_id      = local.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.api_alb[0].id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api" })
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
    security_groups = compact([local.runtime_primary_security_group_id, try(aws_security_group.api[0].id, null)])
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

resource "aws_security_group" "ecr_endpoint" {
  count = var.create_network ? 1 : 0

  name        = "${local.name_prefix}-ecr-endpoint"
  description = "Allow ECS tasks to reach ECR through VPC endpoints"
  vpc_id      = local.vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = compact([local.runtime_primary_security_group_id, try(aws_security_group.api[0].id, null)])
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecr-endpoint" })
}

resource "aws_vpc_endpoint" "ecr_api" {
  count = var.create_network ? 1 : 0

  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.ecr_endpoint[0].id]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecr-api-endpoint" })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  count = var.create_network ? 1 : 0

  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.ecr_endpoint[0].id]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecr-dkr-endpoint" })
}

resource "aws_vpc_endpoint" "s3" {
  count = var.create_network ? 1 : 0

  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-s3-endpoint" })
}