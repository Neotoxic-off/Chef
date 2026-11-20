# Deno, Bun, Hono

Builds on `typescript.md`. Written for Deno 2.9.8, Bun 1.4.4, Hono 4.13.19, @hono/zod-validator 0.9 (Nov 2026), not benchmarked. Current versions: `deno --version` / GitHub releases of `denoland/deno`; `npm view bun version`; `npm view hono version`.

## Deno

- Use the built-in tools, not ESLint/Prettier/Vitest: `deno fmt --check`, `deno lint`, `deno check`, `deno test`.
- `deno.json` lint config:
  ```json
  {
    "lint": {
      "rules": {
        "tags": ["recommended"],
        "include": ["explicit-function-return-type", "explicit-module-boundary-types", "eqeqeq"]
      }
    },
    "coverage": { "thresholds": { "lines": 90, "branches": 90, "functions": 90 } }
  }
  ```
- Never `-A` / `--allow-all`. Name the exact permissions in a permission set in `deno.json` (2.5+) and run with `-P`:
  ```json
  { "permissions": { "default": { "net": ["0.0.0.0:8000", "db.internal:5432"], "env": ["DATABASE_URL"] } } }
  ```
- Dependencies through `jsr:` / `npm:` specifiers in `imports`; commit `deno.lock`. Tests: `deno test --coverage` (gated by the thresholds above, or `--coverage-threshold=90`). Keep the resource and op sanitizers on; fake time with `FakeTime` from `@std/testing/time`.

## Bun

- Bun runs TypeScript without checking it: CI runs `tsc --noEmit`. No built-in linter: ESLint and Prettier as in `typescript.md`. Commit `bun.lock`; CI installs with `bun install --frozen-lockfile`.
- `bun test` with a gate in `bunfig.toml`. It gates lines and functions only (no branch gate), and only when the default `text` reporter runs; use Vitest when branch coverage must be enforced:
  ```toml
  [test]
  coverage = true
  coverageThreshold = { lines = 0.9, functions = 0.9 }
  ```
- `Bun.serve({ routes })` needs 1.2.3+. Prefer web-standard `Request`/`Response`/`fetch` over `Bun.*` APIs in app code so it stays portable.

## Hono

- One `app` with routes and middleware; the runtime adapter (`Deno.serve(app.fetch)`, `export default app` on Bun, `@hono/node-server` on Node) lives only in the entry file.
- Type the env once: `new Hono<AppEnv>()`. Leave the handler's `c` to Hono's inference: a hand-written `Context` annotation drops the validator types. typescript-eslint's `explicit-function-return-type` accepts this (`allowTypedFunctionExpressions` is on by default).
- Validate every body, query and param with `zValidator` (`@hono/zod-validator`; peer `hono >=4.11.2`, `zod ^3.25 || ^4`) and read only `c.req.valid(...)`. A failed check returns 400.
- Throw `HTTPException` (`hono/http-exception`); render errors in one `app.onError`. No `try`/`catch` in handlers. Middleware: `secureHeaders()`, `cors({ origin: [...] })` with explicit origins, `bodyLimit({ maxSize: MAX_BODY_BYTES })`.

```ts
interface CreateOrderRequest { sku: string; quantity: number }

const MAX_QUANTITY: number = 100;
const HTTP_CREATED: SuccessStatusCode = 201; // type from "hono/utils/http-status"
const createOrderSchema: z.ZodType<CreateOrderRequest> = z.object({
  sku: z.string().min(1),
  quantity: z.number().int().positive().max(MAX_QUANTITY),
});

export const app: Hono<AppEnv> = new Hono<AppEnv>();
app.post("/orders", zValidator("json", createOrderSchema), async (c) => {
  const order: OrderDto = await orders.create(c.req.valid("json"));
  return c.json(order, HTTP_CREATED);
});
```

Tests call the app directly, no server (`testClient(app)` from `hono/testing` for typed calls):

```ts
test("create order with zero quantity returns 400", async (): Promise<void> => {
  const response: Response = await app.request("/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sku: "A-1", quantity: 0 }),
  });
  expect(response.status).toBe(400);
});
```
