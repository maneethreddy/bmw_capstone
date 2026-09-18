variable "aws_region" {
  type        = string
  description = "AWS region for all telemetry resources."
  default     = "us-east-1"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for telemetry storage."
  default     = "m-bmw-capstone-p11-raw"
}

variable "iam_role_name" {
  type        = string
  description = "IAM role name for the PySpark streaming runtime."
  default     = "bmw-capstone-p11-streaming-role"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention period in days."
  default     = 14
}

variable "cloudwatch_log_group_name" {
  type        = string
  description = "CloudWatch log group for streaming application logs."
  default     = "/bmw-capstone-p11/streaming"
}

variable "glue_database_name" {
  type        = string
  description = "AWS Glue Data Catalog database name (used by Athena)."
  default     = "bmw_capstone_p11"
}

variable "glue_table_name" {
  type        = string
  description = "AWS Glue Data Catalog table name for curated telemetry aggregates."
  default     = "telemetry_aggregates"
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all provisioned resources."
  default = {
    Project     = "bmw-capstone-p11"
    Participant = "P11"
    Environment = "capstone"
  }
}