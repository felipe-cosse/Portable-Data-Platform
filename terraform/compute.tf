locals {
  ami_parameter = var.architecture == "arm64" ? (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
    ) : (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
  )
}

data "aws_ssm_parameter" "amazon_linux_2023" {
  name = local.ami_parameter
}

resource "aws_instance" "platform" {
  ami                         = data.aws_ssm_parameter.amazon_linux_2023.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.platform.id
  vpc_security_group_ids      = [aws_security_group.platform.id]
  iam_instance_profile        = aws_iam_instance_profile.platform.name
  associate_public_ip_address = true
  monitoring                  = false

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    aws_region       = var.aws_region
    artifact_bucket  = aws_s3_bucket.data_lake.id
    artifact_key     = aws_s3_object.platform_bundle.key
    compose_profiles = var.enable_metabase ? "bi" : ""
    compose_version  = var.compose_version
    secret_id        = aws_secretsmanager_secret.platform.id
  })

  user_data_replace_on_change = false

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = var.root_volume_size_gb
    iops        = 3000
    throughput  = 125

    tags = {
      Name = "${var.name}-root"
    }
  }

  dynamic "credit_specification" {
    for_each = var.cpu_credits == null ? [] : [var.cpu_credits]
    content {
      cpu_credits = credit_specification.value
    }
  }

  tags = {
    Name = var.name
  }

  depends_on = [
    aws_iam_role_policy.platform,
    aws_iam_role_policy_attachment.ssm,
    aws_s3_object.platform_bundle,
    aws_secretsmanager_secret_version.platform,
  ]
}
