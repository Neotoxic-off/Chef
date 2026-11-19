Create a .NET 10 class library in this folder that computes invoice totals.

Put the project at `src/Billing/Billing.csproj`, in the namespace `Billing`, exposing `public sealed record InvoiceLine(string Sku, int Quantity, decimal UnitPrice)` and a static class `InvoiceCalculator` with `public static decimal Total(IReadOnlyList<InvoiceLine> lines, decimal discountPercent)`. The total is the sum of `Quantity * UnitPrice` over all lines, reduced by `discountPercent` percent, then rounded to 2 decimals with halves rounded away from zero. An empty list totals 0.

Throw an `ArgumentNullException` when `lines` or one of its lines is null. Throw an `ArgumentException` when a line has a null, empty or whitespace-only `Sku`, a `Quantity` below 1, or a negative `UnitPrice` (a price of 0 is allowed). Throw an `ArgumentOutOfRangeException` when `discountPercent` is below 0 or above 100 (both bounds are allowed).

Work autonomously: nobody will answer questions.
