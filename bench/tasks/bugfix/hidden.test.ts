import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { Cart } from "../src/cart.ts";
import type { CartTotals, Product } from "../src/cart.ts";

const MUG: Product = { sku: "MUG-01", name: "Stoneware mug", unitPriceCents: 1200 };
const PLATE: Product = { sku: "PLT-02", name: "Dinner plate", unitPriceCents: 850 };

function cartWith(additions: readonly (readonly [Product, number])[]): Cart {
  const cart: Cart = new Cart();
  for (const [product, quantity] of additions) {
    cart.addItem(product, quantity);
  }
  return cart;
}

describe("reported bug: adding the same product twice", (): void => {
  it("gets the bulk discount like adding the total quantity at once", (): void => {
    const totals: CartTotals = cartWith([
      [MUG, 6],
      [MUG, 4],
    ]).totals();

    assert.deepEqual(totals, cartWith([[MUG, 10]]).totals());
    assert.equal(totals.bulkDiscountCents, 1200);
  });

  it("setting the quantity afterwards sets the product's quantity", (): void => {
    const cart: Cart = cartWith([
      [MUG, 6],
      [MUG, 4],
    ]);

    cart.setQuantity("MUG-01", 12);

    assert.equal(cart.itemCount(), 12);
    assert.deepEqual(cart.totals(), cartWith([[MUG, 12]]).totals());
  });
});

describe("existing behaviour", (): void => {
  it("does not pool different products to reach a bulk tier", (): void => {
    const totals: CartTotals = cartWith([
      [MUG, 6],
      [PLATE, 4],
    ]).totals();

    assert.equal(totals.bulkDiscountCents, 0);
  });

  it("starts the bulk discount at exactly 10 units", (): void => {
    assert.equal(cartWith([[MUG, 9]]).totals().bulkDiscountCents, 0);
    assert.equal(cartWith([[MUG, 10]]).totals().bulkDiscountCents, 1200);
  });

  it("combines bulk discount, fixed coupon, free shipping and tax", (): void => {
    const cart: Cart = cartWith([
      [MUG, 10],
      [PLATE, 2],
    ]);
    cart.applyCoupon({ kind: "fixed", code: "TEN", amountOffCents: 1000, minimumSubtotalCents: 5000 });

    assert.deepEqual(cart.totals(), {
      subtotalCents: 13700,
      bulkDiscountCents: 1200,
      couponDiscountCents: 1000,
      shippingCents: 0,
      taxCents: 2300,
      totalCents: 13800,
    });
  });
});
