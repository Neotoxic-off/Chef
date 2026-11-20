import assert from "node:assert/strict";
import { once } from "node:events";
import { after, before, test } from "node:test";

import app, { isCalendarDate, validateReservation } from "../app.js";

const VALID = { name: "Ada", email: "ada@example.com", partySize: 2, date: "2026-12-24" };
let base;
let server;

before(async () => {
  server = app.listen(0, "127.0.0.1");
  await once(server, "listening");
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => server.close());

function post(body, contentType = "application/json") {
  return fetch(`${base}/reservations`, { method: "POST", headers: { "content-type": contentType }, body });
}

test("isCalendarDate accepts real days only", () => {
  assert.equal(isCalendarDate("2028-02-29"), true);
  assert.equal(isCalendarDate("0050-01-01"), true);
  assert.equal(isCalendarDate("2026-02-29"), false);
  assert.equal(isCalendarDate("2026-1-05"), false);
});

test("validateReservation reports every invalid field", () => {
  assert.deepEqual(validateReservation(VALID), {});
  assert.deepEqual(Object.keys(validateReservation({ partySize: "4" })).sort(), ["date", "email", "name", "partySize"]);
});

test("POST /reservations creates a reservation", async () => {
  const response = await post(JSON.stringify({ ...VALID, name: " Ada " }));

  assert.equal(response.status, 201);
  const { id, ...rest } = await response.json();
  assert.ok(id > 0);
  assert.deepEqual(rest, VALID);
});

test("POST /reservations rejects malformed JSON as JSON", async () => {
  const response = await post("{");

  assert.equal(response.status, 400);
  assert.deepEqual(Object.keys((await response.json()).errors), ["body"]);
});

test("POST /reservations rejects a body that is not an object", async () => {
  const response = await post("[]");

  assert.equal(response.status, 400);
  assert.deepEqual(Object.keys((await response.json()).errors), ["body"]);
});
