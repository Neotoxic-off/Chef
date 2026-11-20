# @acme/billing-client

Typed client for the ACME billing API, used by the checkout and back-office services.

```ts
import { createBillingClient } from "@acme/billing-client";

const billing = createBillingClient({ baseUrl: "https://billing.internal/api/v2", token: process.env.BILLING_TOKEN! });
const invoice = await billing.invoices.create({ customerId: "cus_42", lines: [...] }, { idempotencyKey: orderId });
```

- Every call goes through `HttpClient` (`src/http-client.ts`): base URL, auth header, JSON in and out, errors.
- Failed calls throw `HttpError` (the API answered with an error status) or `NetworkError` (no answer).
- Time is never read or waited on directly: `HttpClient` takes a `Scheduler` (`src/scheduler.ts`), so tests
  run without real delays. The rate limiter uses it.
- `fetch` is injectable for the same reason.

## Development

Node 24+ runs the TypeScript sources directly.

```
npm test
npm run typecheck
```
