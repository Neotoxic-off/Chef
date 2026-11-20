output "bucket_id" {
  description = "ID (name) of the log bucket."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the log bucket."
  value       = aws_s3_bucket.this.arn
}
