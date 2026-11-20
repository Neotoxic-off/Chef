import { ClientConfigError, HttpError, type NetworkError } from "./errors.ts";

export interface RetryOptions {
  /** Total number of attempts, the first one included. Default 3. */
  maxAttempts?: number;
  /** Wait before the first retry; doubles on every further retry. Default 250. */
  baseDelayMs?: number;
  /** Upper bound of every wait, `Retry-After` included. Default 10000. */
  maxDelayMs?: number;
}

const DEFAULT_MAX_ATTEMPTS: number = 3;
const DEFAULT_BASE_DELAY_MS: number = 250;
const DEFAULT_MAX_DELAY_MS: number = 10_000;
const MS_PER_SECOND: number = 1000;
const RETRYABLE_STATUSES: ReadonlySet<number> = new Set([408, 429, 500, 502, 503, 504]);
const RETRY_AFTER_STATUSES: ReadonlySet<number> = new Set([429, 503]);
const SAFE_METHODS: ReadonlySet<string> = new Set(["GET", "HEAD", "PUT", "DELETE", "OPTIONS"]);
const KEY_DEPENDENT_METHODS: ReadonlySet<string> = new Set(["POST", "PATCH"]);
const IDEMPOTENCY_KEY_HEADER: string = "idempotency-key";
const SECONDS_PATTERN: RegExp = /^\d+$/;
const HTTP_DATE_PATTERN: RegExp = /[a-z]/i;

/** Decides whether a failed request is sent again and how long to wait first. */
export class RetryPolicy {
  readonly #maxAttempts: number;
  readonly #baseDelayMs: number;
  readonly #maxDelayMs: number;

  constructor(options: RetryOptions | false = {}) {
    const settings: RetryOptions = options === false ? { maxAttempts: 1 } : options;
    this.#maxAttempts = settings.maxAttempts ?? DEFAULT_MAX_ATTEMPTS;
    this.#baseDelayMs = settings.baseDelayMs ?? DEFAULT_BASE_DELAY_MS;
    this.#maxDelayMs = settings.maxDelayMs ?? DEFAULT_MAX_DELAY_MS;
    if (!Number.isInteger(this.#maxAttempts) || this.#maxAttempts < 1) {
      throw new ClientConfigError(`retry.maxAttempts must be an integer of at least 1, got ${this.#maxAttempts}`);
    }
    assertDelay("baseDelayMs", this.#baseDelayMs);
    assertDelay("maxDelayMs", this.#maxDelayMs);
  }

  /** `attempt` is the number of the attempt that just failed, starting at 1. */
  shouldRetry(
    attempt: number,
    method: string,
    headers: Record<string, string>,
    error: HttpError | NetworkError,
  ): boolean {
    return (
      attempt < this.#maxAttempts &&
      isSafeToRepeat(method, headers) &&
      (!(error instanceof HttpError) || RETRYABLE_STATUSES.has(error.status))
    );
  }

  /** Milliseconds to wait before the attempt that follows failed attempt number `attempt`. */
  delayMs(attempt: number, error: HttpError | NetworkError, retryAfter: string | null, now: number): number {
    const requested: number | undefined =
      error instanceof HttpError && RETRY_AFTER_STATUSES.has(error.status)
        ? parseRetryAfterMs(retryAfter, now)
        : undefined;
    return Math.min(requested ?? this.#baseDelayMs * 2 ** (attempt - 1), this.#maxDelayMs);
  }
}

function assertDelay(name: string, value: number): void {
  if (!Number.isFinite(value) || value < 0) {
    throw new ClientConfigError(`retry.${name} must be a non-negative number, got ${value}`);
  }
}

function isSafeToRepeat(method: string, headers: Record<string, string>): boolean {
  if (SAFE_METHODS.has(method)) {
    return true;
  }
  return (
    KEY_DEPENDENT_METHODS.has(method) &&
    Object.entries(headers).some(([name, value]: [string, string]): boolean => name.toLowerCase() === IDEMPOTENCY_KEY_HEADER && value !== "")
  );
}

/** Reads a `Retry-After` value (delay in seconds or HTTP date); undefined when missing or unreadable. */
function parseRetryAfterMs(value: string | null, now: number): number | undefined {
  const trimmed: string = (value ?? "").trim();
  if (SECONDS_PATTERN.test(trimmed)) {
    return Number(trimmed) * MS_PER_SECOND;
  }
  if (!HTTP_DATE_PATTERN.test(trimmed)) {
    return undefined;
  }
  const date: number = Date.parse(trimmed);
  return Number.isNaN(date) ? undefined : Math.max(0, date - now);
}
