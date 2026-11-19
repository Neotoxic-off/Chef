import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { type BillingClient, ClientConfigError, createBillingClient, type Invoice } from "../src/index.ts";
import { FakeFetch, FakeScheduler, json } from "./fakes.ts";

const BASE_URL: string = "https://billing.test/api/v2";

const INVOICE: Invoice = {
  id: "inv_1",
  customerId: "cus_1",
  status: "open",
  currency: "EUR",
  lines: [{ description: "Plan", quantity: 1, unitPriceCents: 4900 }],
  totalCents: 4900,
  createdAt: "2026-11-20T09:00:00Z",
};

function billing(fake: FakeFetch): BillingClient {
  return createBillingClient({ baseUrl: BASE_URL, fetch: fake.fetch, scheduler: new FakeScheduler() });
}

describe("InvoicesApi", () => {
  it("lists invoices with snake_case filters", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, { invoices: [INVOICE], nextCursor: null }));
    const page = await billing(fake).invoices.list({ customerId: "cus_1", status: "open", limit: 10 });
    assert.equal(page.invoices[0]?.id, "inv_1");
    assert.equal(fake.calls[0]?.url, `${BASE_URL}/invoices?customer_id=cus_1&status=open&limit=10`);
  });

  it("rejects a page size the API refuses", () => {
    assert.throws(() => billing(new FakeFetch()).invoices.list({ limit: 101 }), ClientConfigError);
    assert.throws(() => billing(new FakeFetch()).invoices.list({ limit: 0 }), ClientConfigError);
  });

  it("encodes ids in paths", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, INVOICE));
    await billing(fake).invoices.get("inv/1");
    assert.equal(fake.calls[0]?.url, `${BASE_URL}/invoices/inv%2F1`);
  });

  it("creates an invoice with an idempotency key", async () => {
    const fake: FakeFetch = new FakeFetch(json(201, INVOICE));
    const created: Invoice = await billing(fake).invoices.create(
      { customerId: "cus_1", lines: INVOICE.lines },
      { idempotencyKey: "order-77" },
    );
    assert.equal(created.id, "inv_1");
    assert.equal(fake.headersOf(0)["Idempotency-Key"], "order-77");
  });

  it("creates an invoice without an idempotency key", async () => {
    const fake: FakeFetch = new FakeFetch(json(201, INVOICE));
    await billing(fake).invoices.create({ customerId: "cus_1", lines: INVOICE.lines });
    assert.equal(fake.headersOf(0)["Idempotency-Key"], undefined);
  });

  it("validates lines before sending", () => {
    const invoices = billing(new FakeFetch()).invoices;
    assert.throws(() => invoices.create({ customerId: "cus_1", lines: [] }), ClientConfigError);
    assert.throws(
      () => invoices.create({ customerId: "cus_1", lines: [{ description: "x", quantity: 0, unitPriceCents: 1 }] }),
      ClientConfigError,
    );
    assert.throws(
      () => invoices.updateLines("inv_1", [{ description: "x", quantity: 1, unitPriceCents: 1.5 }]),
      ClientConfigError,
    );
  });

  it("voids with a POST to the void action", async () => {
    const fake: FakeFetch = new FakeFetch(json(200, { ...INVOICE, status: "void" }));
    const voided: Invoice = await billing(fake).invoices.void("inv_1");
    assert.equal(voided.status, "void");
    assert.equal(fake.calls[0]?.init.method, "POST");
    assert.equal(fake.calls[0]?.url, `${BASE_URL}/invoices/inv_1/void`);
  });

  it("deletes a draft", async () => {
    const fake: FakeFetch = new FakeFetch(new Response(null, { status: 204 }));
    await billing(fake).invoices.deleteDraft("inv_1");
    assert.equal(fake.calls[0]?.init.method, "DELETE");
  });
});

describe("CustomersApi", () => {
  it("searches by email and replaces with PUT", async () => {
    const customer = { id: "cus_1", name: "Ada", email: "ada@example.com", vatNumber: null };
    const fake: FakeFetch = new FakeFetch(json(200, [customer]), json(200, customer));
    const client: BillingClient = billing(fake);
    assert.deepEqual(await client.customers.search("ada@example.com"), [customer]);
    await client.customers.replace(customer);
    assert.equal(fake.calls[1]?.init.method, "PUT");
  });
});
