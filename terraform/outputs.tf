output "s3_bucket_name" {
  value       = aws_s3_bucket.telemetry.bucket
  description = "Telemetry S3 bucket name."
}

output "s3_bucket_arn" {
  value       = aws_s3_bucket.telemetry.arn
  description = "Telemetry S3 bucket ARN."
}

output "cloudwatch_log_group_name" {
  value       = aws_cloudwatch_log_group.streaming.name
  description = "Streaming CloudWatch log group."
}

output "streaming_role_arn" {
  value       = aws_iam_role.streaming.arn
  description = "IAM role ARN for the streaming runtime."
}