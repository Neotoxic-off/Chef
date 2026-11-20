import type { FetchFunction, Scheduler } from "../src/index.ts";

export interface RecordedCall {
  url: string;
  init: RequestInit;
}

export type FakeReply = Response | Error;

/** A fetch that answers from a script, in order, and records what it was sent. */
export class FakeFetch {
  readonly calls: RecordedCall[] = [];
  readonly #replies: FakeReply[];

  constructor(...replies: FakeReply[]) {
    this.#replies = replies;
  }

  readonly fetch: FetchFunction = (url: string, init: RequestInit): Promise<Response> => {
    this.calls.push({ url, init });
    const reply: FakeReply | undefined = this.#replies.shift();
    if (reply === undefined) {
      return Promise.reject(new Error(`unexpected request ${init.method ?? "GET"} ${url}`));
    }
    return reply instanceof Error ? Promise.reject(reply) : Promise.resolve(reply);
  };

  headersOf(index: number): Record<string, string> {
    return (this.calls[index]?.init.headers ?? {}) as Record<string, string>;
  }
}

/** A clock that only moves when the code under test sleeps. */
export class FakeScheduler implements Scheduler {
  readonly sleeps: number[] = [];
  #now: number;

  constructor(now: number = Date.UTC(2026, 10, 20, 9, 0, 0)) {
    this.#now = now;
  }

  now(): number {
    return this.#now;
  }

  sleep(milliseconds: number): Promise<void> {
    this.sleeps.push(milliseconds);
    this.#now += milliseconds;
    return Promise.resolve();
  }
}

export function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

export function text(status: number, body: string, headers: Record<string, string> = {}): Response {
  return new Response(body, { status, headers: { "Content-Type": "text/plain", ...headers } });
}
