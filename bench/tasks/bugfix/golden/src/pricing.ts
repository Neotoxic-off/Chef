export interface BulkTier {
  readonly minimumQuantity: number;
  readonly percentOff: number;
}

export interface PercentCoupon {
  readonly kind: "percent";
  readonly code: string;
  readonly percentOff: number;
}

export interface FixedCoupon {
  readonly kind: "fixed";
  readonly code: string;
  readonly amountOffCents: number;
  readonly minimumSubtotalCents: number;
}

export type Coupon = PercentCoupon | FixedCoupon;

export interface PricingRules {
  readonly bulkTiers: readonly BulkTier[];
  readonly taxRatePercent: number;
  readonly shippingCents: number;
  readonly freeShippingThresholdCents: number;
}

export const DEFAULT_RULES: PricingRules = {
  bulkTiers: [
    { minimumQuantity: 10, percentOff: 10 },
    { minimumQuantity: 25, percentOff: 15 },
  ],
  taxRatePercent: 20,
  shippingCents: 590,
  freeShippingThresholdCents: 10000,
};

const PERCENT: number = 100;
const CENTS_PER_UNIT: number = 100;

export function percentOf(amountCents: number, percent: number): number {
  return Math.round((amountCents * percent) / PERCENT);
}

export function bulkPercentOff(quantity: number, tiers: readonly BulkTier[]): number {
  const reached: readonly BulkTier[] = tiers.filter((tier: BulkTier): boolean => quantity >= tier.minimumQuantity);
  return Math.max(0, ...reached.map((tier: BulkTier): number => tier.percentOff));
}

export function couponDiscountCents(coupon: Coupon | undefined, eligibleCents: number): number {
  if (coupon === undefined) {
    return 0;
  }
  if (coupon.kind === "percent") {
    return percentOf(eligibleCents, coupon.percentOff);
  }
  if (eligibleCents < coupon.minimumSubtotalCents) {
    return 0;
  }
  return Math.min(coupon.amountOffCents, eligibleCents);
}

export function shippingCents(discountedCents: number, itemCount: number, rules: PricingRules): number {
  if (itemCount === 0 || discountedCents >= rules.freeShippingThresholdCents) {
    return 0;
  }
  return rules.shippingCents;
}

export function assertValidCoupon(coupon: Coupon): void {
  if (coupon.code.trim() === "") {
    throw new RangeError("Coupon code must not be empty");
  }
  if (coupon.kind === "percent" && !(coupon.percentOff > 0 && coupon.percentOff <= PERCENT)) {
    throw new RangeError(`Coupon ${coupon.code}: percentOff must be in (0, 100]`);
  }
  if (coupon.kind === "fixed" && !(Number.isInteger(coupon.amountOffCents) && coupon.amountOffCents > 0)) {
    throw new RangeError(`Coupon ${coupon.code}: amountOffCents must be a positive integer`);
  }
}

export function formatCents(cents: number): string {
  const sign: string = cents < 0 ? "-" : "";
  const absolute: number = Math.abs(cents);
  const units: number = Math.floor(absolute / CENTS_PER_UNIT);
  const rest: string = String(absolute % CENTS_PER_UNIT).padStart(2, "0");
  return `${sign}${units}.${rest}`;
}
