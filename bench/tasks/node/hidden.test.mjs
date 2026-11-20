import assert from "node:assert/strict";
import { once } from "node:events";
import { after, before, test } from "node:test";

import app from "./app.js";

const VALID = { name: "Ada Lovelace", email: "ada@example.com", partySize: 4, date: "2026-12-24" };
let server;
let base;

before(async () => {
  server = app.listen(0, "127.0.0.1");
  await once(server, "listening");
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => server.close());

async function post(body, contentType = "application/json") {
  const response = await fetch(`${base}/reservations`, {
    method: "POST",
    headers: { "content-type": contentType },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { status: response.status, type: response.headers.get("content-type") ?? "", json };
}

async function errorFields(body, contentType) {
  const response = await post(body, contentType);
  assert.equal(response.status, 400);
  assert.match(response.type, /application\/json/);
  assert.equal(typeof response.json?.errors, "object");
  for (const message of Object.values(response.json.errors)) {
    assert.equal(typeof message, "string");
    assert.ok(message.length > 0);
  }
  return Object.keys(response.json.errors).sort();
}

test("a valid reservation is created with its id and the trimmed name", async () => {
  const response = await post({ ...VALID, name: "  Ada Lovelace  " });

  assert.equal(response.status, 201);
  assert.match(response.type, /application\/json/);
  const { id, ...rest } = response.json;
  assert.ok(Number.isInteger(id) && id > 0);
  assert.deepEqual(rest, VALID);
});

test("two reservations get different ids", async () => {
  const first = await post(VALID);
  const second = await post(VALID);

  assert.equal(first.status, 201);
  assert.equal(second.status, 201);
  assert.notEqual(first.json.id, second.json.id);
});

test("every invalid field is reported at once", async () => {
  assert.deepEqual(await errorFields({ name: " ", email: "nope", partySize: 0, date: "tomorrow" }), [
    "date",
    "email",
    "name",
    "partySize",
  ]);
  assert.deepEqual(await errorFields({}), ["date", "email", "name", "partySize"]);
});

test("the name is at most 100 characters once trimmed", async () => {
  assert.equal((await post({ ...VALID, name: ` ${"a".repeat(100)} ` })).status, 201);
  assert.deepEqual(await errorFields({ ...VALID, name: "a".repeat(101) }), ["name"]);
  assert.deepEqual(await errorFields({ ...VALID, name: 42 }), ["name"]);
});

test("the email has one @, no whitespace and a dot in the domain", async () => {
  for (const email of ["ada@example", "ada example@x.org", "ada@@example.com", "@example.com", "ada@ex ample.com", 7]) {
    assert.deepEqual(await errorFields({ ...VALID, email }), ["email"], `email ${email}`);
  }
});

test("the party size is a JSON integer from 1 to 12", async () => {
  assert.equal((await post({ ...VALID, partySize: 1 })).status, 201);
  assert.equal((await post({ ...VALID, partySize: 12 })).status, 201);
  for (const partySize of [0, 13, 2.5, -1, "4", null, true]) {
    assert.deepEqual(await errorFields({ ...VALID, partySize }), ["partySize"], `partySize ${partySize}`);
  }
});

test("the date is a day that exists, written YYYY-MM-DD", async () => {
  assert.equal((await post({ ...VALID, date: "2028-02-29" })).status, 201);
  for (const date of ["2026-02-29", "2026-04-31", "2026-13-01", "2026-00-10", "2026-1-05", "24/12/2026", "2026-12-24T19:00"]) {
    assert.deepEqual(await errorFields({ ...VALID, date }), ["date"], `date ${date}`);
  }
});

test("malformed JSON gets a JSON error on the body", async () => {
  assert.deepEqual(await errorFields('{"name": "Ada",'), ["body"]);
});

test("a body that is not a JSON object gets an error on the body", async () => {
  assert.deepEqual(await errorFields([VALID]), ["body"]);
  assert.deepEqual(await errorFields("name=Ada", "application/x-www-form-urlencoded"), ["body"]);
});
