import {
  assertValidCoupon,
  bulkPercentOff,
  couponDiscountCents,
  DEFAULT_RULES,
  percentOf,
  shippingCents,
} from "./pricing.ts";
import type { Coupon, PricingRules } from "./pricing.ts";

export interface Product {
  readonly sku: string;
  readonly name: string;
  readonly unitPriceCents: number;
}

export interface CartLine {
  readonly product: Product;
  readonly quantity: number;
}

export interface CartTotals {
  readonly subtotalCents: number;
  readonly bulkDiscountCents: number;
  readonly couponDiscountCents: number;
  readonly shippingCents: number;
  readonly taxCents: number;
  readonly totalCents: number;
}

function assertValidQuantity(quantity: number): void {
  if (!Number.isInteger(quantity) || quantity <= 0) {
    throw new RangeError(`Quantity must be a positive integer, got ${quantity}`);
  }
}

function assertValidProduct(product: Product): void {
  if (product.sku.trim() === "") {
    throw new RangeError("Product SKU must not be empty");
  }
  if (!Number.isInteger(product.unitPriceCents) || product.unitPriceCents < 0) {
    throw new RangeError(`Product ${product.sku}: unitPriceCents must be a non-negative integer`);
  }
}

function lineSubtotalCents(line: CartLine): number {
  return line.product.unitPriceCents * line.quantity;
}

export class Cart {
  readonly #rules: PricingRules;
  #lines: CartLine[] = [];
  #coupon: Coupon | undefined = undefined;

  constructor(rules: PricingRules = DEFAULT_RULES) {
    this.#rules = rules;
  }

  addItem(product: Product, quantity: number = 1): void {
    assertValidProduct(product);
    assertValidQuantity(quantity);
    this.#lines.push({ product, quantity });
  }

  setQuantity(sku: string, quantity: number): void {
    if (quantity === 0) {
      this.removeItem(sku);
      return;
    }
    assertValidQuantity(quantity);
    const index: number = this.#lines.findIndex((line: CartLine): boolean => line.product.sku === sku);
    const line: CartLine | undefined = this.#lines[index];
    if (line === undefined) {
      throw new RangeError(`No item with SKU ${sku} in the cart`);
    }
    this.#lines[index] = { product: line.product, quantity };
  }

  removeItem(sku: string): void {
    this.#lines = this.#lines.filter((line: CartLine): boolean => line.product.sku !== sku);
  }

  applyCoupon(coupon: Coupon): void {
    assertValidCoupon(coupon);
    this.#coupon = coupon;
  }

  removeCoupon(): void {
    this.#coupon = undefined;
  }

  lines(): readonly CartLine[] {
    return [...this.#lines];
  }

  itemCount(): number {
    return this.#lines.reduce((count: number, line: CartLine): number => count + line.quantity, 0);
  }

  totals(): CartTotals {
    const subtotal: number = this.#sum(lineSubtotalCents);
    const bulkDiscount: number = this.#sum((line: CartLine): number =>
      percentOf(lineSubtotalCents(line), bulkPercentOff(line.quantity, this.#rules.bulkTiers)),
    );
    const couponDiscount: number = couponDiscountCents(this.#coupon, subtotal - bulkDiscount);
    const discounted: number = subtotal - bulkDiscount - couponDiscount;
    const shipping: number = shippingCents(discounted, this.itemCount(), this.#rules);
    const tax: number = percentOf(discounted + shipping, this.#rules.taxRatePercent);
    return {
      subtotalCents: subtotal,
      bulkDiscountCents: bulkDiscount,
      couponDiscountCents: couponDiscount,
      shippingCents: shipping,
      taxCents: tax,
      totalCents: discounted + shipping + tax,
    };
  }

  #sum(amountOf: (line: CartLine) => number): number {
    return this.#lines.reduce((total: number, line: CartLine): number => total + amountOf(line), 0);
  }
}
