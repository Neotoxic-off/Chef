import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ClientConfigError, RateLimiter } from "../src/index.ts";
import { FakeScheduler } from "./fakes.ts";

describe("RateLimiter", () => {
  it("lets the first request through at once", async () => {
    const scheduler: FakeScheduler = new FakeScheduler();
    await new RateLimiter(500, scheduler).acquire();
    assert.deepEqual(scheduler.sleeps, []);
  });

  it("queues concurrent callers one interval apart", async () => {
    const scheduler: FakeScheduler = new FakeScheduler();
    const limiter: RateLimiter = new RateLimiter(500, scheduler);
    await Promise.all([limiter.acquire(), limiter.acquire(), limiter.acquire()]);
    assert.deepEqual(scheduler.sleeps, [500, 500]);
  });

  it("never waits when disabled", async () => {
    const scheduler: FakeScheduler = new FakeScheduler();
    const limiter: RateLimiter = new RateLimiter(0, scheduler);
    await limiter.acquire();
    await limiter.acquire();
    assert.deepEqual(scheduler.sleeps, []);
  });

  it("rejects a negative interval", () => {
    assert.throws(() => new RateLimiter(-1, new FakeScheduler()), ClientConfigError);
  });
});
