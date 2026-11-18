# AWS

Verified Nov 2026: `aws-actions/configure-aws-credentials` v6.x, cfn-lint v1.x. Check the current release with `gh release list -R <owner>/<repo> -L 1` before you pin.

## Lint and validate

- Lint templates (CloudFormation, SAM, CDK output): `cfn-lint "**/*.yaml"`. Fail CI on errors and warnings.
- Scan IaC for misconfig: `trivy config .` or `checkov -d .`. Fail CI on HIGH/CRITICAL.
- Validate every IAM policy you write: `aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY --policy-document file://policy.json`. Fix all ERROR and SECURITY_WARNING findings.
- In CI, block broader access: `aws accessanalyzer check-no-new-access` against the previous policy version.

## Practices

- Use AWS Organizations: one account per workload and environment. Never deploy workloads in the management account.
- Humans sign in through IAM Identity Center with short sessions. No IAM users, no access keys.
- Guardrails with SCPs at OU level: deny leaving the org, deny disabling CloudTrail/GuardDuty/Config, deny unused regions.
- Enable account-wide S3 Block Public Access, default EBS encryption and IMDSv2 required (`HttpTokens: required`).
- Tag every resource (`owner`, `env`, `cost-center`); enforce with tag policies.
- Define all infrastructure as code (Terraform, CDK, CloudFormation). No console changes in prod.

## Security

- CI assumes a role through GitHub OIDC. Scope the trust policy to repo and environment, never `repo:org/*`.

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:acme/api:environment:prod"
    }
  }
}
```

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@<sha> # v6.x; current: gh release list -R aws-actions/configure-aws-credentials -L 1
    with:
      role-to-assume: arn:aws:iam::111122223333:role/deploy-api-prod
      aws-region: eu-west-1
```

- Least privilege: name actions and resource ARNs. No `"Action": "*"` or `"Resource": "*"` unless the API has no resource-level permissions.
- Use permission boundaries on roles that CI or developers can create.
- Review IAM Access Analyzer unused-access and external-access findings; remove what is unused.
- Workloads use roles (instance profile, task role, IRSA or EKS Pod Identity). Never bake keys into images or env vars.
- Secrets live in Secrets Manager or SSM Parameter Store `SecureString`, encrypted with KMS, with rotation on.
- Org-wide CloudTrail to a locked log account; GuardDuty, Security Hub and Config on in every account and region in use.
- A scanner finding is fixed, or you ask the user. Never add inline skips (`# checkov:skip`, cfn-lint `Metadata` ignores).

## Tests

- Test IAM changes before deploy: `aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names s3:GetObject --resource-arns <arn>`.
- Run integration tests in a sandbox account, created and torn down by the pipeline.
- After deploy, run a smoke test against the real endpoint and check CloudWatch alarms stay OK.
