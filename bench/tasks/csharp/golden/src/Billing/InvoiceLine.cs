namespace Billing;

public sealed record InvoiceLine(string Sku, int Quantity, decimal UnitPrice);
