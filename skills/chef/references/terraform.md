# Terraform and OpenTofu

Commands below use `terraform`; `tofu` takes the same ones.

## Lint and validate

- Format check in CI: `terraform fmt -check -recursive`.
- `terraform init -backend=false && terraform validate` in every root module and module.
- tflint with the provider ruleset, fail on warnings: `tflint --init && tflint --recursive`.
- Security and misconfig scan: `trivy config .` (tfsec is now part of Trivy) or `checkov -d .`. Fail CI on HIGH/CRITICAL.

`.tflint.hcl`:

```hcl
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
plugin "aws" {
  enabled = true
  version = "0.40.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
```

## Practices

- Pin Terraform and every provider. Commit `.terraform.lock.hcl`.

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {
    bucket       = "acme-tfstate"
    key          = "network/prod.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true  # S3-native locking; dynamodb_table is deprecated
  }
}
```

- Remote state with locking, always. Never commit `*.tfstate`. One state per environment and component; keep blast radius small.
- Small modules with one job. Each has `variables.tf`, `outputs.tf`, `versions.tf`, a README (`terraform-docs`).
- Pin module sources to a version or tag (`?ref=v1.2.0`, `version = "~> 3.1"`), never a branch.
- Every variable has `type` and `description`; add `validation` blocks at trust boundaries. No untyped `any`.
- Prefer `for_each` over `count` for anything that has identity. Use `moved` blocks instead of state surgery.
- CI runs `plan` on PRs and posts it; only the pipeline runs `apply`, from the reviewed plan file.

## Security

- No secrets in `.tf`, `.tfvars` or state outputs. Read them from a secret manager; mark variables and outputs `sensitive = true`.
- Encrypt state at rest and restrict who can read it: state holds secrets in plain text. OpenTofu can also encrypt state client-side.
- CI authenticates to the cloud with OIDC, not long-lived access keys.
- Least-privilege IAM for the pipeline role; separate plan (read) and apply (write) roles.

## Tests

- Write `terraform test` files (`tests/*.tftest.hcl`) for every module.
- Fast unit tests: `command = plan` with `mock_provider` (Terraform 1.7+), no credentials needed.
- Integration tests: `command = apply` in a sandbox account; the framework destroys what it created.
- Assert on outputs and planned attributes, and test `validation` rules with `expect_failures`.

```hcl
mock_provider "aws" {}

run "bucket_is_private" {
  command = plan
  assert {
    condition     = aws_s3_bucket_public_access_block.this.block_public_acls
    error_message = "Bucket must block public ACLs."
  }
}
```
