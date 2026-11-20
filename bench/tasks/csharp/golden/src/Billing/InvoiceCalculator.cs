namespace Billing;

public static class InvoiceCalculator
{
    private const decimal MaxDiscountPercent = 100m;
    private const int CurrencyDecimals = 2;
    private const int MinQuantity = 1;

    public static decimal Total(IReadOnlyList<InvoiceLine> lines, decimal discountPercent)
    {
        ArgumentNullException.ThrowIfNull(lines);
        ArgumentOutOfRangeException.ThrowIfLessThan(discountPercent, 0m);
        ArgumentOutOfRangeException.ThrowIfGreaterThan(discountPercent, MaxDiscountPercent);

        decimal subtotal = 0m;
        foreach (InvoiceLine line in lines)
        {
            ValidateLine(line);
            subtotal += line.Quantity * line.UnitPrice;
        }

        decimal discounted = subtotal * (MaxDiscountPercent - discountPercent) / MaxDiscountPercent;
        return Math.Round(discounted, CurrencyDecimals, MidpointRounding.AwayFromZero);
    }

    private static void ValidateLine(InvoiceLine? line)
    {
        ArgumentNullException.ThrowIfNull(line, nameof(line));

        // Plain ArgumentException on purpose: the contract names this exact type, not its subclasses.
        if (string.IsNullOrWhiteSpace(line.Sku))
        {
            throw new ArgumentException("Invoice line Sku must not be null, empty or whitespace.", nameof(line));
        }

        if (line.Quantity < MinQuantity)
        {
            throw new ArgumentException($"Invoice line '{line.Sku}' Quantity must be at least {MinQuantity}.", nameof(line));
        }

        if (line.UnitPrice < 0m)
        {
            throw new ArgumentException($"Invoice line '{line.Sku}' UnitPrice must not be negative.", nameof(line));
        }
    }
}
