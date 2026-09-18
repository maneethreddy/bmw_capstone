# -----------------------------------------------------------------------
# S3 Bucket — raw and curated telemetry storage
# -----------------------------------------------------------------------

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

# -----------------------------------------------------------------------
# CloudWatch Log Group — streaming application logs
# -----------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "streaming" {
  name              = var.cloudwatch_log_group_name
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# -----------------------------------------------------------------------
# IAM Role — assumed by the EC2 / EMR / local runtime
# -----------------------------------------------------------------------

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
        Sid      = "S3Write"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = "${aws_s3_bucket.telemetry.arn}/*"
      },
      {
        Sid      = "S3List"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = aws_s3_bucket.telemetry.arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          aws_cloudwatch_log_group.streaming.arn,
          "${aws_cloudwatch_log_group.streaming.arn}:*"
        ]
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = ["cloudwatch:PutMetricData"]
        # CloudWatch PutMetricData does not support resource-level restrictions
        Resource = "*"
      },
      {
        Sid    = "GlueRead"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:${var.aws_region}:*:catalog",
          "arn:aws:glue:${var.aws_region}:*:database/${var.glue_database_name}",
          "arn:aws:glue:${var.aws_region}:*:table/${var.glue_database_name}/${var.glue_table_name}"
        ]
      },
      {
        Sid    = "AthenaQuery"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------
# AWS Glue Data Catalog — metadata store used by Athena
# (No Glue ETL job — Athena queries S3 directly)
# -----------------------------------------------------------------------

resource "aws_glue_catalog_database" "bmw" {
  name        = var.glue_database_name
  description = "BMW Capstone P11 — curated telemetry aggregates database"
}

resource "aws_glue_catalog_table" "telemetry_aggregates" {
  name          = var.glue_table_name
  database_name = aws_glue_catalog_database.bmw.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"     = "parquet"
    "parquet.compress"   = "SNAPPY"
    "EXTERNAL"           = "TRUE"
    "projection.enabled" = "false"
  }

  storage_descriptor {
    location      = "s3://${var.bucket_name}/curated/telemetry/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "vehicle_id"
      type = "string"
    }
    columns {
      name = "window_start"
      type = "timestamp"
    }
    columns {
      name = "window_end"
      type = "timestamp"
    }
    columns {
      name = "average_speed"
      type = "double"
    }
    columns {
      name = "average_battery_level"
      type = "double"
    }
    columns {
      name = "maximum_temperature"
      type = "double"
    }
    columns {
      name = "fault_count"
      type = "bigint"
    }
    columns {
      name = "event_count"
      type = "bigint"
    }
  }

  partition_keys {
    name = "date"
    type = "string"
  }
}
