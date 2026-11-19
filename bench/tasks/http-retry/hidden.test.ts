import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createBillingClient, HttpClient, HttpError, NetworkError } from "../src/index.ts";
import type { BillingClient, ClientOptions, FetchFunction, Invoice, Scheduler } from "../src/index.ts";

const BASE_URL: string = "https://billing.test/api/v2";
const START: number = Date.UTC(2026, 10, 20, 9, 0, 0);

type Reply = Response | Error;

class ScriptedFetch {
  readonly methods: string[] = [];
  readonly headers: Record<string, string>[] = [];
  readonly bodies: unknown[] = [];
  readonly #replies: Reply[];

  constructor(...replies: Reply[]) {
    this.#replies = replies;
  }

  readonly fetch: FetchFunction = (_url: string, init: RequestInit): Promise<Response> => {
    this.methods.push(init.method ?? "GET");
    this.headers.push(Object.fromEntries(new Headers(init.headers).entries()));
    this.bodies.push(init.body);
    const reply: Reply | undefined = this.#replies.shift();
    if (reply === undefined) {
      return Promise.reject(new Error("no more scripted replies"));
    }
    return reply instanceof Error ? Promise.reject(reply) : Promise.resolve(reply);
  };

  get attempts(): number {
    return this.methods.length;
  }
}

class RecordingScheduler implements Scheduler {
  readonly sleeps: number[] = [];
  #now: number = START;

  now(): number {
    return this.#now;
  }

  sleep(milliseconds: number): Promise<void> {
    this.sleeps.push(milliseconds);
    this.#now += milliseconds;
    return Promise.resolve();
  }
}

function status(code: number, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify({ error: `status ${code}` }), {
    status: code,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function ok(body: unknown = { ok: true }): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function dropped(): Error {
  return new TypeError("fetch failed");
}

function client(
  fake: ScriptedFetch,
  scheduler: RecordingScheduler,
  retry?: ClientOptions["retry"],
): HttpClient {
  const options: ClientOptions = { baseUrl: BASE_URL, fetch: fake.fetch, scheduler };
  return new HttpClient(retry === undefined ? options : { ...options, retry });
}

function billing(fake: ScriptedFetch, scheduler: RecordingScheduler): BillingClient {
  return createBillingClient({ baseUrl: BASE_URL, fetch: fake.fetch, scheduler });
}

function nonZeroSleeps(scheduler: RecordingScheduler): number[] {
  return scheduler.sleeps.filter((milliseconds: number) => milliseconds > 0);
}

const INVOICE: Invoice = {
  id: "inv_1",
  customerId: "cus_1",
  status: "open",
  currency: "EUR",
  lines: [{ description: "Plan", quantity: 1, unitPriceCents: 4900 }],
  totalCents: 4900,
  createdAt: "2026-11-20T09:00:00Z",
};

describe("retry defaults", () => {
  it("retries a GET up to 3 attempts with 250 then 500 ms waits, and returns the success", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), dropped(), ok({ id: "inv_1" }));
    const scheduler: RecordingScheduler = new RecordingScheduler();
    const result: unknown = await client(fake, scheduler).get("/invoices/inv_1");
    assert.deepEqual(result, { id: "inv_1" });
    assert.equal(fake.attempts, 3);
    assert.deepEqual(nonZeroSleeps(scheduler), [250, 500]);
  });

  it("throws the last HttpError when every attempt fails", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(dropped(), status(502), status(504));
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await assert.rejects(client(fake, scheduler).get("/invoices"), (error: unknown) => {
      assert.ok(error instanceof HttpError);
      assert.equal(error.status, 504);
      return true;
    });
    assert.equal(fake.attempts, 3);
  });

  it("throws NetworkError when the last attempt got no answer", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(500), dropped(), dropped());
    await assert.rejects(client(fake, new RecordingScheduler()).get("/invoices"), NetworkError);
    assert.equal(fake.attempts, 3);
  });

  for (const code of [408, 429, 500, 502, 503, 504]) {
    it(`retries status ${code}`, async () => {
      const fake: ScriptedFetch = new ScriptedFetch(status(code), ok());
      await client(fake, new RecordingScheduler()).get("/invoices");
      assert.equal(fake.attempts, 2);
    });
  }

  for (const code of [400, 401, 403, 404, 409, 422, 501]) {
    it(`does not retry status ${code}`, async () => {
      const fake: ScriptedFetch = new ScriptedFetch(status(code), ok());
      const scheduler: RecordingScheduler = new RecordingScheduler();
      await assert.rejects(client(fake, scheduler).get("/invoices"), HttpError);
      assert.equal(fake.attempts, 1);
      assert.deepEqual(nonZeroSleeps(scheduler), []);
    });
  }
});

describe("retry settings", () => {
  it("doubles the wait and caps it at maxDelayMs", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), status(503), status(503), status(503), status(503), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler, { maxAttempts: 6, baseDelayMs: 1000, maxDelayMs: 3000 }).get("/invoices");
    assert.equal(fake.attempts, 6);
    assert.deepEqual(nonZeroSleeps(scheduler), [1000, 2000, 3000, 3000, 3000]);
  });

  it("keeps the defaults for settings left out", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), status(503), status(503), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler, { maxAttempts: 4 }).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), [250, 500, 1000]);
  });

  it("sends one attempt when retry is false", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), ok());
    await assert.rejects(client(fake, new RecordingScheduler(), false).get("/invoices"), HttpError);
    assert.equal(fake.attempts, 1);
  });

  it("sends one attempt when maxAttempts is 1", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(dropped(), ok());
    await assert.rejects(client(fake, new RecordingScheduler(), { maxAttempts: 1 }).get("/invoices"), NetworkError);
    assert.equal(fake.attempts, 1);
  });

  it("rejects settings that make no sense when the client is created", () => {
    const scheduler: RecordingScheduler = new RecordingScheduler();
    assert.throws(() => client(new ScriptedFetch(), scheduler, { maxAttempts: 0 }));
    assert.throws(() => client(new ScriptedFetch(), scheduler, { baseDelayMs: -1 }));
    assert.throws(() => client(new ScriptedFetch(), scheduler, { maxDelayMs: -5 }));
  });
});

describe("Retry-After", () => {
  it("waits the seconds a 429 asks for", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(429, { "Retry-After": "3" }), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), [3000]);
  });

  it("waits until the HTTP date a 503 gives", async () => {
    const retryAt: string = new Date(START + 4000).toUTCString();
    const fake: ScriptedFetch = new ScriptedFetch(status(503, { "Retry-After": retryAt }), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), [4000]);
  });

  it("caps Retry-After at maxDelayMs", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503, { "Retry-After": "120" }), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler, { maxDelayMs: 5000 }).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), [5000]);
  });

  it("falls back to the backoff when Retry-After is unreadable", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(429, { "Retry-After": "soon" }), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), [250]);
  });
});

describe("only requests safe to repeat are retried", () => {
  for (const method of ["HEAD", "PUT", "DELETE", "OPTIONS"] as const) {
    it(`retries ${method}`, async () => {
      const fake: ScriptedFetch = new ScriptedFetch(status(503), new Response(null, { status: 204 }));
      await client(fake, new RecordingScheduler()).request(method, "/customers/cus_1");
      assert.equal(fake.attempts, 2);
    });
  }

  it("never sends a POST twice without an idempotency key", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(dropped(), ok());
    await assert.rejects(client(fake, new RecordingScheduler()).post("/invoices/inv_1/void", {}), NetworkError);
    assert.equal(fake.attempts, 1);
  });

  it("never voids an invoice twice", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), ok(INVOICE));
    await assert.rejects(billing(fake, new RecordingScheduler()).invoices.void("inv_1"), HttpError);
    assert.equal(fake.attempts, 1);
  });

  it("never sends a PATCH twice without an idempotency key", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(502), ok(INVOICE));
    await assert.rejects(billing(fake, new RecordingScheduler()).invoices.updateLines("inv_1", INVOICE.lines), HttpError);
    assert.equal(fake.attempts, 1);
  });

  it("retries creating an invoice with an idempotency key, with the same key and body", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(dropped(), status(503), ok(INVOICE));
    const created: Invoice = await billing(fake, new RecordingScheduler()).invoices.create(
      { customerId: "cus_1", lines: INVOICE.lines },
      { idempotencyKey: "order-77" },
    );
    assert.equal(created.id, "inv_1");
    assert.equal(fake.attempts, 3);
    assert.deepEqual(
      fake.headers.map((headers: Record<string, string>) => headers["idempotency-key"]),
      ["order-77", "order-77", "order-77"],
    );
    assert.equal(new Set(fake.bodies).size, 1);
  });

  it("does not retry creating an invoice without an idempotency key", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), ok(INVOICE));
    await assert.rejects(
      billing(fake, new RecordingScheduler()).invoices.create({ customerId: "cus_1", lines: INVOICE.lines }),
      HttpError,
    );
    assert.equal(fake.attempts, 1);
  });

  it("recognizes the idempotency key header in any case", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), ok());
    await client(fake, new RecordingScheduler()).request("POST", "/payments", {
      body: { amountCents: 100 },
      headers: { "idempotency-key": "pay-1" },
    });
    assert.equal(fake.attempts, 2);
  });
});

describe("behaviour that must not change", () => {
  it("still spaces every request by minIntervalMs", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(ok(), ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    const http: HttpClient = new HttpClient({ baseUrl: BASE_URL, fetch: fake.fetch, scheduler, minIntervalMs: 100 });
    await http.get("/a");
    await http.get("/b");
    assert.deepEqual(nonZeroSleeps(scheduler), [100]);
  });

  it("does not wait at all when the first attempt succeeds", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(ok());
    const scheduler: RecordingScheduler = new RecordingScheduler();
    await client(fake, scheduler).get("/invoices");
    assert.deepEqual(nonZeroSleeps(scheduler), []);
  });

  it("keeps the decoded error body of the last failure", async () => {
    const fake: ScriptedFetch = new ScriptedFetch(status(503), status(503), status(503));
    await assert.rejects(client(fake, new RecordingScheduler()).get("/invoices"), (error: unknown) => {
      assert.ok(error instanceof HttpError);
      assert.deepEqual(error.body, { error: "status 503" });
      return true;
    });
  });
});
