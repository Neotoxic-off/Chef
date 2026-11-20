import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ClientConfigError,
  HttpClient,
  HttpError,
  InvoicesApi,
  NetworkError,
  type HttpMethod,
  type RetryOptions,
} from "../src/index.ts";
import { FakeFetch, FakeScheduler, json, text } from "./fakes.ts";

const BASE_URL: string = "https://billing.test/api/v2";
const OK: () => Response = () => json(200, { ok: true });
const unavailable: (headers?: Record<string, string>) => Response = (headers = {}) => text(503, "down", headers);

function setup(
  retry: RetryOptions | false | undefined,
  ...replies: (Response | Error)[]
): { http: HttpClient; fake: FakeFetch; scheduler: FakeScheduler } {
  const fake: FakeFetch = new FakeFetch(...replies);
  const scheduler: FakeScheduler = new FakeScheduler();
  const http: HttpClient = new HttpClient({
    baseUrl: BASE_URL,
    fetch: fake.fetch,
    scheduler,
    ...(retry === undefined ? {} : { retry }),
  });
  return { http, fake, scheduler };
}

describe("retry", () => {
  it("retries a 503 and returns the later success", async () => {
    const { http, fake } = setup(undefined, unavailable(), OK());
    assert.deepEqual(await http.get("/ping"), { ok: true });
    assert.equal(fake.calls.length, 2);
  });

  it("retries when the request gets no answer", async () => {
    const { http, fake } = setup(undefined, new TypeError("reset"), OK());
    await http.get("/ping");
    assert.equal(fake.calls.length, 2);
  });

  for (const status of [408, 429, 500, 502, 503, 504]) {
    it(`retries status ${status}`, async () => {
      const { http, fake } = setup(undefined, text(status, "x"), OK());
      await http.get("/ping");
      assert.equal(fake.calls.length, 2);
    });
  }

  for (const status of [400, 401, 404, 409, 422, 501]) {
    it(`does not retry status ${status}`, async () => {
      const { http, fake } = setup(undefined, text(status, "x"), OK());
      await assert.rejects(http.get("/ping"), HttpError);
      assert.equal(fake.calls.length, 1);
    });
  }

  it("does not retry a success body that is not JSON", async () => {
    const { http, fake } = setup(undefined, text(200, "<html>"), OK());
    await assert.rejects(http.get("/ping"));
    assert.equal(fake.calls.length, 1);
  });

  it("doubles the wait from baseDelayMs up to maxDelayMs", async () => {
    const replies: Response[] = [unavailable(), unavailable(), unavailable(), unavailable(), OK()];
    const { http, scheduler } = setup({ maxAttempts: 5, baseDelayMs: 250, maxDelayMs: 600 }, ...replies);
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [250, 500, 600, 600]);
  });

  it("uses 3 attempts, 250 ms and 10000 ms by default", async () => {
    const { http, fake, scheduler } = setup(undefined, unavailable(), unavailable(), unavailable(), OK());
    await assert.rejects(http.get("/ping"), HttpError);
    assert.equal(fake.calls.length, 3);
    assert.deepEqual(scheduler.sleeps, [250, 500]);
  });

  it("throws the last failure when the attempts run out", async () => {
    const { http } = setup({ maxAttempts: 2 }, text(500, "first"), text(502, "last"));
    await assert.rejects(http.get("/ping"), (error: unknown) => {
      assert.ok(error instanceof HttpError);
      assert.equal(error.status, 502);
      assert.equal(error.body, "last");
      return true;
    });
  });

  it("throws NetworkError when the last failure is no answer", async () => {
    const { http } = setup({ maxAttempts: 2 }, unavailable(), new TypeError("reset"));
    await assert.rejects(http.get("/ping"), NetworkError);
  });

  it("does not retry when retry is false", async () => {
    const { http, fake, scheduler } = setup(false, unavailable(), OK());
    await assert.rejects(http.get("/ping"), HttpError);
    assert.equal(fake.calls.length, 1);
    assert.deepEqual(scheduler.sleeps, []);
  });

  it("does not retry with maxAttempts 1", async () => {
    const { http, fake } = setup({ maxAttempts: 1 }, unavailable(), OK());
    await assert.rejects(http.get("/ping"), HttpError);
    assert.equal(fake.calls.length, 1);
  });
});

describe("Retry-After", () => {
  it("waits the seconds a 503 asks for", async () => {
    const { http, scheduler } = setup(undefined, unavailable({ "Retry-After": "2" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [2000]);
  });

  it("waits the seconds a 429 asks for", async () => {
    const { http, scheduler } = setup(undefined, text(429, "x", { "Retry-After": "1" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [1000]);
  });

  it("waits until the HTTP date a 503 gives", async () => {
    const { http, scheduler } = setup(undefined, unavailable({ "Retry-After": "Fri, 20 Nov 2026 09:00:03 GMT" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [3000]);
  });

  it("does not wait for an HTTP date in the past", async () => {
    const { http, scheduler } = setup(undefined, unavailable({ "Retry-After": "Fri, 20 Nov 2026 08:00:00 GMT" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [0]);
  });

  it("caps the requested wait at maxDelayMs", async () => {
    const { http, scheduler } = setup({ maxDelayMs: 4000 }, unavailable({ "Retry-After": "120" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [4000]);
  });

  for (const header of ["soon", "-5", "1.5", ""]) {
    it(`falls back to the backoff for the unreadable value "${header}"`, async () => {
      const { http, scheduler } = setup(undefined, unavailable({ "Retry-After": header }), OK());
      await http.get("/ping");
      assert.deepEqual(scheduler.sleeps, [250]);
    });
  }

  it("falls back to the backoff when the header is missing", async () => {
    const { http, scheduler } = setup(undefined, text(429, "x"), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [250]);
  });

  it("ignores Retry-After on other statuses", async () => {
    const { http, scheduler } = setup(undefined, text(500, "x", { "Retry-After": "5" }), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [250]);
  });
});

describe("retry and request safety", () => {
  for (const method of ["GET", "HEAD", "PUT", "DELETE", "OPTIONS"] as const satisfies readonly HttpMethod[]) {
    it(`retries ${method}`, async () => {
      const { http, fake } = setup(undefined, unavailable(), new Response(null, { status: 204 }));
      await http.request(method, "/x");
      assert.equal(fake.calls.length, 2);
    });
  }

  for (const method of ["POST", "PATCH"] as const satisfies readonly HttpMethod[]) {
    it(`does not retry ${method} without an Idempotency-Key`, async () => {
      const { http, fake } = setup(undefined, unavailable(), OK());
      await assert.rejects(http.request(method, "/x", { body: {} }), HttpError);
      assert.equal(fake.calls.length, 1);
    });

    it(`retries ${method} with an Idempotency-Key, whatever its case`, async () => {
      const { http, fake } = setup(undefined, unavailable(), OK());
      await http.request(method, "/x", { body: {}, headers: { "idempotency-key": "k1" } });
      assert.equal(fake.calls.length, 2);
      assert.equal(fake.headersOf(1)["idempotency-key"], "k1");
    });
  }

  it("does not retry a POST with an empty Idempotency-Key", async () => {
    const { http, fake } = setup(undefined, unavailable(), OK());
    await assert.rejects(http.request("POST", "/x", { headers: { "Idempotency-Key": "" } }), HttpError);
    assert.equal(fake.calls.length, 1);
  });

  it("does not retry a POST that got no answer and has no key", async () => {
    const { http, fake } = setup(undefined, new TypeError("reset"), OK());
    await assert.rejects(http.post("/x", {}), NetworkError);
    assert.equal(fake.calls.length, 1);
  });

  it("retries an invoice created with an idempotency key", async () => {
    const { http, fake } = setup(undefined, unavailable(), json(201, { id: "inv_1" }));
    const invoice = { customerId: "cus_1", lines: [{ description: "x", quantity: 1, unitPriceCents: 100 }] };
    await new InvoicesApi(http).create(invoice, { idempotencyKey: "order-7" });
    assert.equal(fake.calls.length, 2);
  });

  it("never sends a void twice", async () => {
    const { http, fake } = setup(undefined, unavailable(), OK());
    await assert.rejects(new InvoicesApi(http).void("inv_1"), HttpError);
    assert.equal(fake.calls.length, 1);
  });

  it("sees an Idempotency-Key set as a client default header", async () => {
    const fake: FakeFetch = new FakeFetch(unavailable(), OK());
    const http: HttpClient = new HttpClient({
      baseUrl: BASE_URL,
      fetch: fake.fetch,
      scheduler: new FakeScheduler(),
      headers: { "Idempotency-Key": "k" },
    });
    await http.post("/x", {});
    assert.equal(fake.calls.length, 2);
  });
});

describe("retry options", () => {
  const invalid: [string, RetryOptions][] = [
    ["zero attempts", { maxAttempts: 0 }],
    ["negative attempts", { maxAttempts: -1 }],
    ["fractional attempts", { maxAttempts: 1.5 }],
    ["NaN attempts", { maxAttempts: Number.NaN }],
    ["negative base delay", { baseDelayMs: -1 }],
    ["negative max delay", { maxDelayMs: -1 }],
    ["infinite base delay", { baseDelayMs: Number.POSITIVE_INFINITY }],
    ["NaN max delay", { maxDelayMs: Number.NaN }],
  ];

  for (const [name, retry] of invalid) {
    it(`rejects ${name} when the client is created`, () => {
      assert.throws(() => new HttpClient({ baseUrl: BASE_URL, retry }), ClientConfigError);
    });
  }

  it("accepts zero delays", async () => {
    const { http, scheduler } = setup({ baseDelayMs: 0, maxDelayMs: 0 }, unavailable(), OK());
    await http.get("/ping");
    assert.deepEqual(scheduler.sleeps, [0]);
  });
});
