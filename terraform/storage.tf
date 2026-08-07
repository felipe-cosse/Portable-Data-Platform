resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "data_lake" {
  bucket        = "${var.name}-${data.aws_caller_identity.current.account_id}-${random_id.bucket_suffix.hex}"
  force_destroy = var.bucket_force_destroy

  tags = {
    Name = "${var.name}-data-lake"
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.data_lake]
}

data "archive_file" "platform" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/platform-bundle.zip"

  excludes = [
    ".git",
    ".env",
    ".pytest_cache",
    ".ruff_cache",
    "dbt/logs",
    "dbt/target",
    "terraform/.terraform",
    "terraform/.terraform.lock.hcl",
    "terraform/platform-bundle.zip",
    "terraform/terraform.tfstate",
    "terraform/terraform.tfstate.backup",
  ]
}

resource "aws_s3_object" "platform_bundle" {
  bucket                 = aws_s3_bucket.data_lake.id
  key                    = "artifacts/platform-bundle.zip"
  source                 = data.archive_file.platform.output_path
  etag                   = data.archive_file.platform.output_md5
  server_side_encryption = "AES256"

  depends_on = [
    aws_s3_bucket_public_access_block.data_lake,
    aws_s3_bucket_server_side_encryption_configuration.data_lake,
  ]
}
