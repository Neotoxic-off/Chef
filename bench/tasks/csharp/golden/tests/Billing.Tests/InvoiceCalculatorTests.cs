namespace Billing.Tests;

public sealed class InvoiceCalculatorTests
{
    private static InvoiceLine Line(string sku = "A", int quantity = 1, decimal unitPrice = 1m) =>
        new(sku, quantity, unitPrice);

    [Fact]
    public void Total_WithEmptyList_ReturnsZero()
    {
        decimal total = InvoiceCalculator.Total([], 0m);

        Assert.Equal(0m, total);
    }

    [Fact]
    public void Total_WithSeveralLines_SumsQuantityTimesUnitPrice()
    {
        InvoiceLine[] lines = [Line("A", 2, 10.50m), Line("B", 3, 1.25m)];

        decimal total = InvoiceCalculator.Total(lines, 0m);

        Assert.Equal(24.75m, total);
    }

    [Fact]
    public void Total_WithDiscount_ReducesByPercent()
    {
        decimal total = InvoiceCalculator.Total([Line(quantity: 2, unitPrice: 50m)], 25m);

        Assert.Equal(75m, total);
    }

    [Fact]
    public void Total_WithFullDiscount_ReturnsZero()
    {
        decimal total = InvoiceCalculator.Total([Line(unitPrice: 9.99m)], 100m);

        Assert.Equal(0m, total);
    }

    [Fact]
    public void Total_WithZeroUnitPrice_IsAllowed()
    {
        decimal total = InvoiceCalculator.Total([Line(unitPrice: 0m)], 0m);

        Assert.Equal(0m, total);
    }

    [Theory]
    [InlineData("0.005", "0.01")]
    [InlineData("0.015", "0.02")]
    [InlineData("0.004", "0.00")]
    [InlineData("0.0051", "0.01")]
    public void Total_RoundsHalvesAwayFromZero(string unitPrice, string expected)
    {
        decimal total = InvoiceCalculator.Total([Line(unitPrice: decimal.Parse(unitPrice, System.Globalization.CultureInfo.InvariantCulture))], 0m);

        Assert.Equal(decimal.Parse(expected, System.Globalization.CultureInfo.InvariantCulture), total);
    }

    [Fact]
    public void Total_RoundsHalfAwayFromZeroAfterDiscount()
    {
        decimal total = InvoiceCalculator.Total([Line(unitPrice: 10.01m)], 50m);

        Assert.Equal(5.01m, total);
    }

    [Fact]
    public void Total_WithNullLines_ThrowsArgumentNullException()
    {
        Assert.Throws<ArgumentNullException>(() => InvoiceCalculator.Total(null!, 0m));
    }

    [Fact]
    public void Total_WithNullLine_ThrowsArgumentNullException()
    {
        InvoiceLine?[] lines = [Line(), null];

        Assert.Throws<ArgumentNullException>(() => InvoiceCalculator.Total(lines!, 0m));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Total_WithBlankSku_ThrowsArgumentException(string? sku)
    {
        InvoiceLine[] lines = [new(sku!, 1, 1m)];

        Assert.Throws<ArgumentException>(() => InvoiceCalculator.Total(lines, 0m));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public void Total_WithQuantityBelowOne_ThrowsArgumentException(int quantity)
    {
        InvoiceLine[] lines = [Line(quantity: quantity)];

        Assert.Throws<ArgumentException>(() => InvoiceCalculator.Total(lines, 0m));
    }

    [Fact]
    public void Total_WithNegativeUnitPrice_ThrowsArgumentException()
    {
        InvoiceLine[] lines = [Line(unitPrice: -0.01m)];

        Assert.Throws<ArgumentException>(() => InvoiceCalculator.Total(lines, 0m));
    }

    [Theory]
    [InlineData("-0.01")]
    [InlineData("100.01")]
    public void Total_WithDiscountOutOfRange_ThrowsArgumentOutOfRangeException(string discount)
    {
        decimal discountPercent = decimal.Parse(discount, System.Globalization.CultureInfo.InvariantCulture);

        Assert.Throws<ArgumentOutOfRangeException>(() => InvoiceCalculator.Total([Line()], discountPercent));
    }
}
