import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { Cart } from "../src/cart.ts";
import type { CartLine, CartTotals, Product } from "../src/cart.ts";
import { renderReceipt } from "../src/receipt.ts";

const MUG: Product = { sku: "MUG-01", name: "Stoneware mug", unitPriceCents: 1200 };
const PLATE: Product = { sku: "PLT-02", name: "Dinner plate", unitPriceCents: 850 };

describe("Cart", (): void => {
  it("empty cart costs nothing", (): void => {
    const totals: CartTotals = new Cart().totals();

    assert.equal(totals.totalCents, 0);
    assert.equal(totals.shippingCents, 0);
  });

  it("charges shipping and tax below the free shipping threshold", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(MUG, 2);

    const totals: CartTotals = cart.totals();

    assert.deepEqual(totals, {
      subtotalCents: 2400,
      bulkDiscountCents: 0,
      couponDiscountCents: 0,
      shippingCents: 590,
      taxCents: 598,
      totalCents: 3588,
    });
  });

  it("gives the bulk discount from 10 units of a product", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(PLATE, 10);

    assert.equal(cart.totals().bulkDiscountCents, 850);
  });

  it("adding the same product twice merges into one line and gets the bulk discount", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(MUG, 6);
    cart.addItem(MUG, 4);

    assert.equal(cart.lines().length, 1);
    assert.equal(cart.itemCount(), 10);
    assert.equal(cart.totals().bulkDiscountCents, 1200);
  });

  it("setting the quantity of a product added twice replaces the whole quantity", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(MUG, 6);
    cart.addItem(MUG, 4);

    cart.setQuantity("MUG-01", 12);

    assert.equal(cart.itemCount(), 12);
  });

  it("applies a percent coupon after the bulk discount", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(MUG, 10);
    cart.applyCoupon({ kind: "percent", code: "SPRING5", percentOff: 5 });

    assert.equal(cart.totals().couponDiscountCents, 540);
  });

  it("ignores a fixed coupon below its minimum subtotal", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(PLATE, 2);
    cart.applyCoupon({ kind: "fixed", code: "TEN", amountOffCents: 1000, minimumSubtotalCents: 5000 });

    assert.equal(cart.totals().couponDiscountCents, 0);
  });

  it("setting a quantity to zero removes the line", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(MUG, 3);
    cart.addItem(PLATE, 1);

    cart.setQuantity("MUG-01", 0);

    assert.deepEqual(
      cart.lines().map((line: CartLine): string => line.product.sku),
      ["PLT-02"],
    );
  });

  it("rejects a quantity that is not a positive integer", (): void => {
    const cart: Cart = new Cart();

    assert.throws((): void => cart.addItem(MUG, 0), RangeError);
    assert.throws((): void => cart.addItem(MUG, 1.5), RangeError);
  });

  it("renders a receipt with the discount lines", (): void => {
    const cart: Cart = new Cart();
    cart.addItem(PLATE, 10);

    const receipt: string = renderReceipt(cart);

    assert.match(receipt, /10 x Dinner plate\s+85\.00/);
    assert.match(receipt, /Bulk discount\s+-8\.50/);
  });
});
