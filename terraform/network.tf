resource "aws_vpc" "platform" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.name}-vpc"
  }
}

resource "aws_internet_gateway" "platform" {
  vpc_id = aws_vpc.platform.id

  tags = {
    Name = "${var.name}-igw"
  }
}

resource "aws_subnet" "platform" {
  vpc_id                  = aws_vpc.platform.id
  cidr_block              = "10.42.10.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.name}-public"
  }
}

resource "aws_route_table" "platform" {
  vpc_id = aws_vpc.platform.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.platform.id
  }

  tags = {
    Name = "${var.name}-public"
  }
}

resource "aws_route_table_association" "platform" {
  subnet_id      = aws_subnet.platform.id
  route_table_id = aws_route_table.platform.id
}

resource "aws_security_group" "platform" {
  name_prefix = "${var.name}-"
  description = "No ingress; administer the data platform through AWS Systems Manager"
  vpc_id      = aws_vpc.platform.id

  egress {
    description = "HTTPS, package repositories, APIs, and external data sources"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name}-instance"
  }

  lifecycle {
    create_before_destroy = true
  }
}
