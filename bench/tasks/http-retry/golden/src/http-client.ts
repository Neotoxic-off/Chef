import { ClientConfigError, HttpError, NetworkError, ResponseFormatError } from "./errors.ts";
import { RateLimiter } from "./rate-limiter.ts";
import { RetryPolicy, type RetryOptions } from "./retry.ts";
import { type Scheduler, systemScheduler } from "./scheduler.ts";

export type HttpMethod = "GET" | "HEAD" | "POST" | "PUT" | "PATCH" | "DELETE" | "OPTIONS";

export type FetchFunction = (url: string, init: RequestInit) => Promise<Response>;

export type QueryValue = string | number | boolean | undefined;

export interface ClientOptions {
  /** Base URL of the API, e.g. https://billing.internal/api/v2 */
  baseUrl: string;
  /** Bearer token sent on every request. */
  token?: string;
  /** Headers sent on every request; per-request headers win. */
  headers?: Record<string, string>;
  /** Minimum time between two requests, 0 to disable. */
  minIntervalMs?: number;
  fetch?: FetchFunction;
  scheduler?: Scheduler;
  /** Retry of failed requests that are safe to send twice; `false` turns it off. */
  retry?: RetryOptions | false;
}

type Outcome =
  | { response: Response }
  | { response?: undefined; error: HttpError | NetworkError; retryAfter: string | null };

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: unknown;
  headers?: Record<string, string>;
}

const USER_AGENT: string = "acme-billing-client/3.2.0";
const DEFAULT_MIN_INTERVAL_MS: number = 0;
const NO_CONTENT: number = 204;

export class HttpClient {
  readonly #baseUrl: string;
  readonly #headers: Record<string, string>;
  readonly #fetch: FetchFunction;
  readonly #scheduler: Scheduler;
  readonly #rateLimiter: RateLimiter;
  readonly #retryPolicy: RetryPolicy;

  constructor(options: ClientOptions) {
    this.#baseUrl = parseBaseUrl(options.baseUrl);
    this.#headers = defaultHeaders(options);
    this.#fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.#scheduler = options.scheduler ?? systemScheduler;
    this.#rateLimiter = new RateLimiter(options.minIntervalMs ?? DEFAULT_MIN_INTERVAL_MS, this.#scheduler);
    this.#retryPolicy = new RetryPolicy(options.retry);
  }

  get<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
    return this.request<T>("GET", path, query === undefined ? {} : { query });
  }

  post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
    return this.request<T>("POST", path, headers === undefined ? { body } : { body, headers });
  }

  patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("PATCH", path, { body });
  }

  delete(path: string): Promise<void> {
    return this.request<void>("DELETE", path);
  }

  async request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
    const url: string = this.#url(path, options.query);
    const init: RequestInit = this.#init(method, options);
    const headers: Record<string, string> = init.headers as Record<string, string>;
    for (let attempt: number = 1; ; attempt++) {
      await this.#rateLimiter.acquire();
      const outcome: Outcome = await this.#attempt(method, url, init);
      if (outcome.response !== undefined) {
        return readJson<T>(outcome.response, url);
      }
      if (!this.#retryPolicy.shouldRetry(attempt, method, headers, outcome.error)) {
        throw outcome.error;
      }
      const delay: number = this.#retryPolicy.delayMs(attempt, outcome.error, outcome.retryAfter, this.#scheduler.now());
      await this.#scheduler.sleep(delay);
    }
  }

  async #attempt(method: HttpMethod, url: string, init: RequestInit): Promise<Outcome> {
    let response: Response;
    try {
      response = await this.#fetch(url, init);
    } catch (error: unknown) {
      return { error: new NetworkError(method, url, error), retryAfter: null };
    }
    if (response.ok) {
      return { response };
    }
    const error: HttpError = new HttpError(response.status, method, url, await readErrorBody(response));
    return { error, retryAfter: response.headers.get("Retry-After") };
  }

  #url(path: string, query: Record<string, QueryValue> | undefined): string {
    if (!path.startsWith("/")) {
      throw new ClientConfigError(`path must start with "/", got "${path}"`);
    }
    const url: URL = new URL(this.#baseUrl + path);
    for (const [name, value] of Object.entries(query ?? {})) {
      if (value !== undefined) {
        url.searchParams.append(name, String(value));
      }
    }
    return url.toString();
  }

  #init(method: HttpMethod, options: RequestOptions): RequestInit {
    const headers: Record<string, string> = { ...this.#headers, ...options.headers };
    if (options.body === undefined) {
      return { method, headers };
    }
    return { method, headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(options.body) };
  }
}

function parseBaseUrl(baseUrl: string): string {
  if (!URL.canParse(baseUrl)) {
    throw new ClientConfigError(`baseUrl is not a valid URL: "${baseUrl}"`);
  }
  return baseUrl.replace(/\/+$/, "");
}

function defaultHeaders(options: ClientOptions): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json", "User-Agent": USER_AGENT, ...options.headers };
  if (options.token !== undefined) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }
  return headers;
}

async function readErrorBody(response: Response): Promise<unknown> {
  const text: string = await response.text();
  if (!(response.headers.get("Content-Type") ?? "").includes("json")) {
    return text;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function readJson<T>(response: Response, url: string): Promise<T> {
  if (response.status === NO_CONTENT) {
    return undefined as T;
  }
  const text: string = await response.text();
  if (text === "") {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ResponseFormatError(url, "body is not JSON");
  }
}
