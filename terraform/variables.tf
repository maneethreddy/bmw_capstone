variable "aws_region" {
  type        = string
  description = "AWS region for the telemetry resources."
  default     = "us-east-1"
}

variable "bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name."
  default     = "bmw-capstone-p11-raw"
}

variable "iam_role_name" {
  type        = string
  description = "IAM role name for the streaming runtime."
  default     = "bmw-capstone-p11-streaming-role"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention period."
  default     = 14
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to provisioned resources."
  default = {
    Project = "bmw-capstone-p11"
  }
}