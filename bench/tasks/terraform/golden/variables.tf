variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket."
}

variable "log_retention_days" {
  type        = number
  description = "Days after which log objects are deleted. Must exceed the 30 days before objects move to STANDARD_IA."
  default     = 365

  validation {
    condition     = var.log_retention_days > 30 && floor(var.log_retention_days) == var.log_retention_days
    error_message = "log_retention_days must be a whole number greater than 30."
  }
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the bucket."
  default     = {}
}
