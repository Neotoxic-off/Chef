# Pulumi

Check the current CLI with `pulumi version` and the latest with `gh release list -R pulumi/pulumi -L 1`. Pin provider packages in the lock file of the language (`package-lock.json`, `uv.lock`, `go.sum`).

## Lint and validate

- Lint and type-check the program with the language tools (`tsc --noEmit` + ESLint, `ruff` + `mypy --strict`, `go vet`).
- `pulumi preview --diff` on every PR; post the diff for review. Only the pipeline runs `pulumi up`.
- Run policy packs in preview: `pulumi preview --policy-pack ./policy`. Mandatory policies fail the run.
- Scan the generated plan or code with `checkov` or `trivy` where they support Pulumi; otherwise rely on policy packs.

## Practices

- One stack per environment (`dev`, `staging`, `prod`); one project per component to keep blast radius small.
- Use a managed backend (Pulumi Cloud) or a self-managed backend with locking and encryption at rest.
- Reusable infrastructure goes in component resources (`ComponentResource`) with typed args.
- Use `protect: true` on stateful resources (databases, buckets with data).
- Rename or move resources with `aliases`, not delete and recreate.
- Read cross-stack values with `StackReference`; do not copy outputs by hand.
- Use `Output.apply` only to transform values; never create resources inside `apply`.

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

interface SecureBucketArgs { forceDestroy: boolean; }

class SecureBucket extends pulumi.ComponentResource {
    public readonly bucketName: pulumi.Output<string>;
    constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
        super("acme:storage:SecureBucket", name, {}, opts);
        const bucket: aws.s3.Bucket = new aws.s3.Bucket(name, { forceDestroy: args.forceDestroy }, { parent: this, protect: true });
        this.bucketName = bucket.bucket;
        this.registerOutputs({ bucketName: this.bucketName });
    }
}
```

## Security

- CI authenticates to the cloud with OIDC: Pulumi ESC `fn::open::aws-login` / `azure-login` / `gcp-login` with `oidc`, or the cloud's own OIDC action. No static keys in config.
- Store secrets with `pulumi config set --secret` or in ESC environments. Never in plain config or code.
- Self-managed backends: use a cloud KMS secrets provider (`--secrets-provider awskms://...`), not the passphrase provider in shared setups.
- State holds secret values (encrypted) and resource details: restrict who can read it.
- Least-privilege deploy identity per stack; separate preview (read) and update (write) roles.
- A policy violation is fixed, or you ask the user. Never downgrade a policy to `advisory` or disable it to pass CI.

## Tests

- Unit tests with mocks (`pulumi.runtime.setMocks`, `pulumi.runtime.set_mocks`), set before the program is imported. No cloud calls.
- Property tests with policy packs: assert security properties on every resource during preview.
- Integration tests: deploy an ephemeral stack in a sandbox (Automation API or the language test runner), assert, then `pulumi destroy` and `pulumi stack rm`.
