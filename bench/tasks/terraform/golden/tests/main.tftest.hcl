mock_provider "aws" {}

variables {
  bucket_name = "app-logs-test"
}

run "defaults_enable_versioning_and_lifecycle" {
  command = plan

  assert {
    condition     = aws_s3_bucket_versioning.this.versioning_configuration[0].status == "Enabled"
    error_message = "Versioning must be enabled."
  }

  assert {
    condition     = one(flatten([for r in aws_s3_bucket_lifecycle_configuration.this.rule : [for b in r.transition : b.days]])) == 30
    error_message = "Objects must move to STANDARD_IA after 30 days."
  }

  assert {
    condition     = one(flatten([for r in aws_s3_bucket_lifecycle_configuration.this.rule : [for b in r.transition : b.storage_class]])) == "STANDARD_IA"
    error_message = "Transition storage class must be STANDARD_IA."
  }

  assert {
    condition     = one(flatten([for r in aws_s3_bucket_lifecycle_configuration.this.rule : [for b in r.expiration : b.days]])) == 365
    error_message = "Default retention must be 365 days."
  }

  assert {
    condition     = one(flatten([for r in aws_s3_bucket_lifecycle_configuration.this.rule : [for b in r.noncurrent_version_expiration : b.noncurrent_days]])) == 30
    error_message = "Noncurrent versions must expire after 30 days."
  }
}

run "custom_retention_and_tags_are_applied" {
  command = plan

  variables {
    log_retention_days = 90
    tags               = { env = "test" }
  }

  assert {
    condition     = one(flatten([for r in aws_s3_bucket_lifecycle_configuration.this.rule : [for b in r.expiration : b.days]])) == 90
    error_message = "Expiration must follow log_retention_days."
  }

  assert {
    condition     = aws_s3_bucket.this.tags["env"] == "test"
    error_message = "Tags must be applied to the bucket."
  }
}

run "bucket_is_private" {
  command = plan

  assert {
    condition     = aws_s3_bucket_public_access_block.this.block_public_acls && aws_s3_bucket_public_access_block.this.block_public_policy && aws_s3_bucket_public_access_block.this.ignore_public_acls && aws_s3_bucket_public_access_block.this.restrict_public_buckets
    error_message = "Bucket must block all public access."
  }
}

run "outputs_are_exposed" {
  command = apply

  assert {
    condition     = output.bucket_id == aws_s3_bucket.this.id
    error_message = "bucket_id must be the bucket id."
  }

  assert {
    condition     = output.bucket_arn == aws_s3_bucket.this.arn
    error_message = "bucket_arn must be the bucket ARN."
  }
}

run "retention_not_above_transition_is_rejected" {
  command = plan

  variables {
    log_retention_days = 30
  }

  expect_failures = [var.log_retention_days]
}
