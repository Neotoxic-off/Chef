import { ClientConfigError } from "./errors.ts";
import type { HttpClient } from "./http-client.ts";

export type InvoiceStatus = "draft" | "open" | "paid" | "void";

export interface InvoiceLine {
  description: string;
  quantity: number;
  unitPriceCents: number;
}

export interface Invoice {
  id: string;
  customerId: string;
  status: InvoiceStatus;
  currency: string;
  lines: InvoiceLine[];
  totalCents: number;
  createdAt: string;
}

export interface NewInvoice {
  customerId: string;
  currency?: string;
  lines: InvoiceLine[];
}

export interface InvoiceFilter {
  customerId?: string;
  status?: InvoiceStatus;
  cursor?: string;
  limit?: number;
}

export interface InvoicePage {
  invoices: Invoice[];
  nextCursor: string | null;
}

export interface CreateOptions {
  /** Same key, same invoice: the API returns the first one instead of creating a duplicate. */
  idempotencyKey?: string;
}

const MAX_PAGE_SIZE: number = 100;
const IDEMPOTENCY_KEY_HEADER: string = "Idempotency-Key";

export class InvoicesApi {
  readonly #http: HttpClient;

  constructor(http: HttpClient) {
    this.#http = http;
  }

  list(filter: InvoiceFilter = {}): Promise<InvoicePage> {
    if (filter.limit !== undefined && (!Number.isInteger(filter.limit) || filter.limit < 1 || filter.limit > MAX_PAGE_SIZE)) {
      throw new ClientConfigError(`limit must be an integer between 1 and ${MAX_PAGE_SIZE}, got ${filter.limit}`);
    }
    return this.#http.get<InvoicePage>("/invoices", {
      customer_id: filter.customerId,
      status: filter.status,
      cursor: filter.cursor,
      limit: filter.limit,
    });
  }

  get(id: string): Promise<Invoice> {
    return this.#http.get<Invoice>(`/invoices/${encodeURIComponent(id)}`);
  }

  create(invoice: NewInvoice, options: CreateOptions = {}): Promise<Invoice> {
    validateLines(invoice.lines);
    const headers: Record<string, string> | undefined =
      options.idempotencyKey === undefined ? undefined : { [IDEMPOTENCY_KEY_HEADER]: options.idempotencyKey };
    return this.#http.post<Invoice>("/invoices", invoice, headers);
  }

  updateLines(id: string, lines: InvoiceLine[]): Promise<Invoice> {
    validateLines(lines);
    return this.#http.patch<Invoice>(`/invoices/${encodeURIComponent(id)}`, { lines });
  }

  /** Voids an open invoice. The API sends the customer a cancellation email each time. */
  void(id: string): Promise<Invoice> {
    return this.#http.post<Invoice>(`/invoices/${encodeURIComponent(id)}/void`, {});
  }

  deleteDraft(id: string): Promise<void> {
    return this.#http.delete(`/invoices/${encodeURIComponent(id)}`);
  }
}

function validateLines(lines: InvoiceLine[]): void {
  if (lines.length === 0) {
    throw new ClientConfigError("an invoice needs at least one line");
  }
  for (const line of lines) {
    if (!Number.isInteger(line.quantity) || line.quantity < 1) {
      throw new ClientConfigError(`quantity must be a positive integer, got ${line.quantity}`);
    }
    if (!Number.isInteger(line.unitPriceCents)) {
      throw new ClientConfigError(`unitPriceCents must be an integer, got ${line.unitPriceCents}`);
    }
  }
}
