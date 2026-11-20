# AWS CDK and CloudFormation

Written in Nov 2026 (not benchmarked): CDK v2 (`aws-cdk-lib`) with `cdk-nag` ^2, cfn-lint v1.x. Check current versions with `npm view aws-cdk-lib version` and `npm view cdk-nag version`. AWS-wide rules: see `aws.md`.

## Lint and validate

- Type-check and lint the CDK app with the language tools (`tsc --noEmit` + ESLint, `ruff` + `mypy --strict`).
- `cdk synth` in CI, then lint the output: `cfn-lint cdk.out/*.template.json`.
- Run cdk-nag as an Aspect on the app; synth fails on errors.

```typescript
const app: cdk.App = new cdk.App();
new ApiStack(app, "ApiProd", { env: { account: "111122223333", region: "eu-west-1" } });
cdk.Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
```

- Policy-as-code on plain CloudFormation: `cfn-guard validate --data template.yaml --rules rules/`.
- `cdk diff` on every PR; post it. Only the pipeline runs `cdk deploy`.

## Practices

- Commit `cdk.json` and `cdk.context.json`; feature flags in `cdk.json` stay at the values the app was tested with.
- Pass `env` (account and region) explicitly on every stack.
- Separate stateful stacks (databases, buckets) from stateless ones. Set `removalPolicy: RemovalPolicy.RETAIN` and `terminationProtection: true` on stateful prod stacks.
- Prefer L2 constructs; use `grant*` methods (`bucket.grantRead(fn)`) instead of hand-written policies.
- Never change a construct ID of a stateful resource: it replaces the resource. Check `cdk diff` for replacements.
- No raw overrides (`addPropertyOverride`) for security settings: cdk-nag runs before them and misses the change.
- CloudFormation without CDK: deploy through change sets, review them, use stack policies on stateful resources, run drift detection on a schedule.

## Security

- Bootstrap with a least-privilege execution policy, not the default `AdministratorAccess`: `cdk bootstrap --cloudformation-execution-policies <policy-arn>`.
- Restrict cross-account trust in bootstrap to the pipeline account (`--trust <account>`).
- CI assumes the deploy role through GitHub OIDC (see `aws.md`). No access keys.
- No secrets in context, props or `CfnParameter` defaults. Use `secretsmanager.Secret.fromSecretNameV2` or `ssm.StringParameter` references, resolved at deploy time.
- A cdk-nag, cfn-lint or cfn-guard finding is fixed, or you ask the user. Never add `NagSuppressions` or cfn-lint ignores on your own; if the user approves one, give a written reason.

## Tests

- Fine-grained assertions with `aws-cdk-lib/assertions`:

```typescript
test("bucket blocks public access", (): void => {
    const app: cdk.App = new cdk.App();
    const stack: ApiStack = new ApiStack(app, "Test");
    const template: Template = Template.fromStack(stack);
    template.hasResourceProperties("AWS::S3::Bucket", {
        PublicAccessBlockConfiguration: Match.objectLike({ BlockPublicAcls: true }),
    });
});
```

- Snapshot tests only as a change detector, next to assertions, never instead of them.
- Test that cdk-nag reports no errors: `Annotations.fromStack(stack).findError("*", Match.anyValue())` is empty.
- Integration tests with `@aws-cdk/integ-tests-alpha` in a sandbox account, or deploy, smoke-test and destroy in CI.
