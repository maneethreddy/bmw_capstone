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
  description = "CloudWatch log group for streaming application logs."
}

output "streaming_role_arn" {
  value       = aws_iam_role.streaming.arn
  description = "IAM role ARN for the streaming runtime."
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.bmw.name
  description = "Glue Data Catalog database name (used by Athena)."
}

output "glue_table_name" {
  value       = aws_glue_catalog_table.telemetry_aggregates.name
  description = "Glue Data Catalog table name for curated telemetry aggregates."
}

output "athena_query_hint" {
  value       = "SELECT * FROM ${aws_glue_catalog_database.bmw.name}.${aws_glue_catalog_table.telemetry_aggregates.name} ORDER BY window_start DESC LIMIT 20;"
  description = "Quick Athena query to verify curated telemetry data."
}