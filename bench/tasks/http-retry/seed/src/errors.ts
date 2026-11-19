/** The API answered with an error status. `body` is the decoded JSON error, or the raw text. */
export class HttpError extends Error {
  readonly status: number;
  readonly method: string;
  readonly url: string;
  readonly body: unknown;

  constructor(status: number, method: string, url: string, body: unknown) {
    super(`${method} ${url} failed with status ${status}`);
    this.name = "HttpError";
    this.status = status;
    this.method = method;
    this.url = url;
    this.body = body;
  }
}

/** The request got no answer: DNS, connection reset, TLS, offline. */
export class NetworkError extends Error {
  readonly method: string;
  readonly url: string;

  constructor(method: string, url: string, cause: unknown) {
    super(`${method} ${url} failed: ${cause instanceof Error ? cause.message : String(cause)}`, { cause });
    this.name = "NetworkError";
    this.method = method;
    this.url = url;
  }
}

/** A success response whose body is not the JSON we expect. */
export class ResponseFormatError extends Error {
  readonly url: string;

  constructor(url: string, detail: string) {
    super(`unexpected response from ${url}: ${detail}`);
    this.name = "ResponseFormatError";
    this.url = url;
  }
}

/** The caller passed something the client cannot send. */
export class ClientConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ClientConfigError";
  }
}
