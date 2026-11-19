Write a reusable Terraform module, at the root of this folder, that creates an AWS S3 bucket for application logs.

Inputs:
- `bucket_name` (string, required): the name of the bucket.
- `log_retention_days` (number, default 365): days after which log objects are deleted.
- `tags` (map of strings, default empty): tags applied to the bucket.

Any other input you add must have a default value.

Behavior:
- Versioning is enabled.
- Log objects move to the `STANDARD_IA` storage class after 30 days and are deleted after `log_retention_days` days.
- Noncurrent object versions are deleted after 30 days.

Outputs: `bucket_id` and `bucket_arn`.

The module uses the AWS provider but does not configure it: the calling configuration does.

Work autonomously: nobody will answer questions.
