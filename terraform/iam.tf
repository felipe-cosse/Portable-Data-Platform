resource "aws_iam_role" "platform" {
  name_prefix = "${var.name}-instance-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.platform.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "platform" {
  name = "${var.name}-runtime"
  role = aws_iam_role.platform.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadPlatformBucketLocation"
        Effect = "Allow"
        Action = ["s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.data_lake.arn
        ]
      },
      {
        Sid    = "ListPlatformBucketPrefixes"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_lake.arn
        ]
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "artifacts",
              "artifacts/*",
              "landing",
              "landing/*",
              "staging",
              "staging/*",
              "exports",
              "exports/*",
            ]
          }
        }
      },
      {
        Sid    = "ReadWritePlatformObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = [
          "${aws_s3_bucket.data_lake.arn}/artifacts/*",
          "${aws_s3_bucket.data_lake.arn}/landing/*",
          "${aws_s3_bucket.data_lake.arn}/staging/*",
          "${aws_s3_bucket.data_lake.arn}/exports/*",
        ]
      },
      {
        Sid      = "ReadRuntimeSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.platform.arn]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "platform" {
  name_prefix = "${var.name}-"
  role        = aws_iam_role.platform.name
}
