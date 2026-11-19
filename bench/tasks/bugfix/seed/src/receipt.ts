import type { Cart, CartLine, CartTotals } from "./cart.ts";
import { formatCents } from "./pricing.ts";

const LABEL_WIDTH: number = 32;
const AMOUNT_WIDTH: number = 10;

function row(label: string, cents: number): string {
  return `${label.padEnd(LABEL_WIDTH)}${formatCents(cents).padStart(AMOUNT_WIDTH)}`;
}

function lineRow(line: CartLine): string {
  return row(`${line.quantity} x ${line.product.name}`, line.product.unitPriceCents * line.quantity);
}

function totalRows(totals: CartTotals): string[] {
  const rows: string[] = [row("Subtotal", totals.subtotalCents)];
  if (totals.bulkDiscountCents > 0) {
    rows.push(row("Bulk discount", -totals.bulkDiscountCents));
  }
  if (totals.couponDiscountCents > 0) {
    rows.push(row("Coupon", -totals.couponDiscountCents));
  }
  rows.push(row("Shipping", totals.shippingCents), row("Tax", totals.taxCents), row("Total", totals.totalCents));
  return rows;
}

export function renderReceipt(cart: Cart): string {
  const separator: string = "-".repeat(LABEL_WIDTH + AMOUNT_WIDTH);
  return [...cart.lines().map(lineRow), separator, ...totalRows(cart.totals())].join("\n");
}
