import type { HttpClient } from "./http-client.ts";

export interface Customer {
  id: string;
  name: string;
  email: string;
  vatNumber: string | null;
}

export interface CustomerChanges {
  name?: string;
  email?: string;
  vatNumber?: string | null;
}

export class CustomersApi {
  readonly #http: HttpClient;

  constructor(http: HttpClient) {
    this.#http = http;
  }

  get(id: string): Promise<Customer> {
    return this.#http.get<Customer>(`/customers/${encodeURIComponent(id)}`);
  }

  search(email: string): Promise<Customer[]> {
    return this.#http.get<Customer[]>("/customers", { email });
  }

  /** Replaces the whole customer record. */
  replace(customer: Customer): Promise<Customer> {
    return this.#http.request<Customer>("PUT", `/customers/${encodeURIComponent(customer.id)}`, { body: customer });
  }

  update(id: string, changes: CustomerChanges): Promise<Customer> {
    return this.#http.patch<Customer>(`/customers/${encodeURIComponent(id)}`, changes);
  }
}
