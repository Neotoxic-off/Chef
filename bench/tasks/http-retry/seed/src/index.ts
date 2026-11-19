import { CustomersApi } from "./customers.ts";
import { type ClientOptions, HttpClient } from "./http-client.ts";
import { InvoicesApi } from "./invoices.ts";

export { CustomersApi } from "./customers.ts";
export type { Customer, CustomerChanges } from "./customers.ts";
export { ClientConfigError, HttpError, NetworkError, ResponseFormatError } from "./errors.ts";
export { HttpClient } from "./http-client.ts";
export type { ClientOptions, FetchFunction, HttpMethod, QueryValue, RequestOptions } from "./http-client.ts";
export { InvoicesApi } from "./invoices.ts";
export type {
  CreateOptions,
  Invoice,
  InvoiceFilter,
  InvoiceLine,
  InvoicePage,
  InvoiceStatus,
  NewInvoice,
} from "./invoices.ts";
export { RateLimiter } from "./rate-limiter.ts";
export { systemScheduler } from "./scheduler.ts";
export type { Scheduler } from "./scheduler.ts";

export interface BillingClient {
  invoices: InvoicesApi;
  customers: CustomersApi;
}

export function createBillingClient(options: ClientOptions): BillingClient {
  const http: HttpClient = new HttpClient(options);
  return { invoices: new InvoicesApi(http), customers: new CustomersApi(http) };
}
