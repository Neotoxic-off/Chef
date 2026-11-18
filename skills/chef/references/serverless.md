# Serverless: Lambda, Azure Functions, Cloud Run

Verified Nov 2026: Lambda SnapStart supports Java 11+, Python 3.12+ and .NET 8+ (also container images). Azure Functions .NET in-process model support ended 10 Nov 2026. Flex Consumption is the recommended plan for new function apps (Linux only). Check current runtimes in each provider's "supported runtimes" doc.

## Lint and validate

- Lint the function code with the language's own tools (see the language rules in SKILL.md).
- SAM: `sam validate --lint` (runs cfn-lint). Serverless IaC also goes through `trivy config .` or `checkov -d .`.
- Pin the runtime version in IaC (`python3.13`, `nodejs22.x`, `FUNCTIONS_WORKER_RUNTIME`). Upgrade before the provider's deprecation date.

## Practices

- Delivery is at-least-once for queues, streams and most event triggers. Every handler must be idempotent.
- Derive an idempotency key from the event (message ID, order ID), store it with a TTL, and return the stored result on repeat.

```python
from aws_lambda_powertools.utilities.idempotency import DynamoDBPersistenceLayer, IdempotencyConfig, idempotent
from aws_lambda_powertools.utilities.typing import LambdaContext

persistence: DynamoDBPersistenceLayer = DynamoDBPersistenceLayer(table_name="idempotency")
config: IdempotencyConfig = IdempotencyConfig(event_key_jmespath="powertools_json(body).order_id", expires_after_seconds=3600)

@idempotent(config=config, persistence_store=persistence)
def handler(event: dict[str, object], context: LambdaContext) -> dict[str, object]:
    return {"statusCode": 200}
```

- Batch triggers (SQS, Kinesis, DynamoDB streams): return partial batch failures (`ReportBatchItemFailures`) so one bad record does not replay the batch.
- Configure a dead-letter queue or on-failure destination for every async trigger. Alarm on its depth.
- Set explicit timeouts shorter than the upstream timeout (and the SQS visibility timeout longer than the function timeout).
- Cap concurrency (reserved concurrency, `maximumInstanceCount`, `--max-instances`) to protect downstream databases.
- Create SDK clients and DB pools once, outside the handler. Keep the package small; load heavy modules lazily.
- Cold starts, cheapest fix first: smaller package, fewer init-time calls, arm64; then SnapStart (Lambda), always-ready instances (Flex Consumption), `--min-instances` and `--cpu-boost` (Cloud Run). Lambda SnapStart and provisioned concurrency cannot be used together.
- SnapStart: do not cache unique values (random seeds, connections, credentials) during init; refresh them after restore.
- Azure Functions .NET: use the isolated worker model on a supported .NET version.
- Cloud Run: allow request concurrency above 1 when the code is thread-safe; fewer instances means fewer cold starts.
- Structured logs with a correlation ID; tracing on (X-Ray / OpenTelemetry, Application Insights, Cloud Trace).

## Security

- One execution role or identity per function, with only the actions and resources it uses.
- No secrets in environment variables in plain text. Read them from the secret manager at init, with caching (see `secrets.md`).
- Host storage for Azure Functions uses managed identity (`AzureWebJobsStorage__accountName`), not a connection string.
- HTTP functions: require auth (IAM auth, Entra ID, Cloud Run `--no-allow-unauthenticated`) unless public by design.
- Validate the event payload at the start of the handler; it is a trust boundary.

## Tests

- Unit-test the business logic as plain functions; keep the handler a thin adapter.
- Test idempotency: call the handler twice with the same event and assert one side effect.
- Run locally with `sam local invoke`, `func start` or the Functions Framework, then integration-test the deployed function in a sandbox.
- Load-test cold paths: measure p99 init duration after a deploy.
