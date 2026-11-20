import { ClientConfigError } from "./errors.ts";
import type { Scheduler } from "./scheduler.ts";

/** Spaces requests at least `minIntervalMs` apart; the billing API bans clients that burst. */
export class RateLimiter {
  readonly #minIntervalMs: number;
  readonly #scheduler: Scheduler;
  #nextSlot: number = 0;

  constructor(minIntervalMs: number, scheduler: Scheduler) {
    if (!Number.isFinite(minIntervalMs) || minIntervalMs < 0) {
      throw new ClientConfigError(`minIntervalMs must be a non-negative number, got ${minIntervalMs}`);
    }
    this.#minIntervalMs = minIntervalMs;
    this.#scheduler = scheduler;
  }

  /** Resolves when the caller may send its request. Concurrent callers queue in call order. */
  async acquire(): Promise<void> {
    const now: number = this.#scheduler.now();
    const slot: number = Math.max(now, this.#nextSlot);
    this.#nextSlot = slot + this.#minIntervalMs;
    if (slot > now) {
      await this.#scheduler.sleep(slot - now);
    }
  }
}
