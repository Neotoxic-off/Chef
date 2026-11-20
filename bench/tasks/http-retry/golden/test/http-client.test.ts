import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ClientConfigError, HttpClient, HttpError, NetworkError, ResponseFormatError } from "../src/index.ts";
import { FakeFetch, FakeScheduler, json, text } from "./fakes.ts";

const BASE_URL: string = "https://billing.test/api/v2";

function client(fake: FakeFetch, scheduler: FakeScheduler = new FakeScheduler()): HttpClient {
  return new HttpClient({ baseUrl: `${BASE_URL}/`, token: "secret", fetch: fake.fetch, scheduler });
}

describe("HttpClient", () => {
  it("joins the base URL and the path and encodes the query", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, []));
    await client(fake).get("/customers", { email: "a+b@example.com", page: 2, archived: undefined });
    assert.equal(fake.calls[0]?.url, `${BASE_URL}/customers?email=a%2Bb%40example.com&page=2`);
  });

  it("sends the auth, accept and user agent headers on every request", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, {}));
    await client(fake).get("/customers/1");
    assert.deepEqual(fake.headersOf(0), {
      Accept: "application/json",
      "User-Agent": "acme-billing-client/3.2.0",
      Authorization: "Bearer secret",
    });
  });

  it("sends a JSON body with its content type", async () => {
    const fake: FakeFetch = new FakeFetch(json(201, { id: "inv_1" }));
    const created: { id: string } = await client(fake).post("/invoices", { customerId: "cus_1" });
    assert.deepEqual(created, { id: "inv_1" });
    assert.equal(fake.calls[0]?.init.method, "POST");
    assert.equal(fake.calls[0]?.init.body, '{"customerId":"cus_1"}');
    assert.equal(fake.headersOf(0)["Content-Type"], "application/json");
  });

  it("lets per-request headers override the defaults", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, {}));
    await client(fake).request("GET", "/x", { headers: { Accept: "text/csv" } });
    assert.equal(fake.headersOf(0)["Accept"], "text/csv");
  });

  it("returns undefined for 204 and empty bodies", async () => {
    const fake: FakeFetch = new FakeFetch(new Response(null, { status: 204 }), new Response("", { status: 200 }));
    assert.equal(await client(fake).delete("/invoices/inv_1"), undefined);
    assert.equal(await client(fake).get("/ping"), undefined);
  });

  it("throws HttpError with the decoded JSON error body", async () => {
    const fake: FakeFetch = new FakeFetch(json(422, { error: "invalid_currency" }));
    await assert.rejects(client(fake).post("/invoices", {}), (error: unknown) => {
      assert.ok(error instanceof HttpError);
      assert.equal(error.status, 422);
      assert.equal(error.method, "POST");
      assert.deepEqual(error.body, { error: "invalid_currency" });
      return true;
    });
  });

  it("keeps a non-JSON error body as text", async () => {
    const fake: FakeFetch = new FakeFetch(text(400, "Bad Request"));
    await assert.rejects(client(fake).get("/invoices"), (error: unknown) => {
      assert.ok(error instanceof HttpError);
      assert.equal(error.body, "Bad Request");
      return true;
    });
  });

  it("throws HttpError on a missing resource", async () => {
    const fake: FakeFetch = new FakeFetch(json(404, { error: "not_found" }));
    await assert.rejects(client(fake).get("/invoices/inv_9"), HttpError);
    assert.equal(fake.calls.length, 1);
  });

  it("wraps a failed fetch in NetworkError", async () => {
    const fake: FakeFetch = new FakeFetch(new TypeError("fetch failed"));
    await assert.rejects(client(fake).post("/invoices", {}), (error: unknown) => {
      assert.ok(error instanceof NetworkError);
      assert.equal(error.message, `POST ${BASE_URL}/invoices failed: fetch failed`);
      return true;
    });
  });

  it("rejects a success body that is not JSON", async () => {
    const fake: FakeFetch = new FakeFetch(text(200, "<html>"));
    await assert.rejects(client(fake).get("/invoices"), ResponseFormatError);
  });

  it("rejects an invalid base URL or path", async () => {
    assert.throws(() => new HttpClient({ baseUrl: "not a url" }), ClientConfigError);
    await assert.rejects(client(new FakeFetch()).get("customers"), ClientConfigError);
  });

  it("spaces requests by minIntervalMs through the scheduler", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, {}), json(200, {}));
    const scheduler: FakeScheduler = new FakeScheduler();
    const http: HttpClient = new HttpClient({ baseUrl: BASE_URL, fetch: fake.fetch, scheduler, minIntervalMs: 100 });
    await http.get("/a");
    await http.get("/b");
    assert.deepEqual(scheduler.sleeps, [100]);
  });
});
