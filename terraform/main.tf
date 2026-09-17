resource "aws_s3_bucket" "telemetry" {
  bucket = var.bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "telemetry" {
  bucket                  = aws_s3_bucket.telemetry.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_cloudwatch_log_group" "streaming" {
  name              = "/bmw-capstone-p11/streaming"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_iam_role" "streaming" {
  name = var.iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "streaming" {
  role = aws_iam_role.streaming.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = "${aws_s3_bucket.telemetry.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.telemetry.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.streaming.arn}:*"
      }
    ]
  })
}
