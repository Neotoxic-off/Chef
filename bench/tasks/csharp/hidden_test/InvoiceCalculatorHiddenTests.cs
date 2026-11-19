using Billing;
using Xunit;

namespace BenchHiddenTests;

public sealed class InvoiceCalculatorHiddenTests
{
    [Fact]
    public void Total_WithNoLines_ReturnsZero()
    {
        decimal total = InvoiceCalculator.Total(new List<InvoiceLine>(), 0m);

        Assert.Equal(0m, total);
    }

    [Theory]
    [InlineData(0, "25.50")]
    [InlineData(10, "22.95")]
    [InlineData(100, "0")]
    public void Total_SumsLinesAndAppliesDiscount(int discountPercent, string expected)
    {
        List<InvoiceLine> lines = new List<InvoiceLine> { new InvoiceLine("A", 2, 10.00m), new InvoiceLine("B", 1, 5.50m) };

        decimal total = InvoiceCalculator.Total(lines, discountPercent);

        Assert.Equal(ParseDecimal(expected), total);
    }

    [Theory]
    [InlineData(1, "0.125", 0, "0.13")]
    [InlineData(3, "0.335", 0, "1.01")]
    [InlineData(1, "10.01", 50, "5.01")]
    [InlineData(5, "0", 0, "0")]
    public void Total_RoundsHalvesAwayFromZero(int quantity, string unitPrice, int discountPercent, string expected)
    {
        List<InvoiceLine> lines = new List<InvoiceLine> { new InvoiceLine("A", quantity, ParseDecimal(unitPrice)) };

        decimal total = InvoiceCalculator.Total(lines, discountPercent);

        Assert.Equal(ParseDecimal(expected), total);
    }

    [Fact]
    public void Total_WithNullList_ThrowsArgumentNullException()
    {
        Assert.Throws<ArgumentNullException>(() => InvoiceCalculator.Total(null!, 0m));
    }

    [Fact]
    public void Total_WithNullLine_ThrowsArgumentNullException()
    {
        List<InvoiceLine> lines = new List<InvoiceLine> { new InvoiceLine("A", 1, 1m), null! };

        Assert.Throws<ArgumentNullException>(() => InvoiceCalculator.Total(lines, 0m));
    }

    [Theory]
    [InlineData(null, 1, "1")]
    [InlineData("", 1, "1")]
    [InlineData("   ", 1, "1")]
    [InlineData("A", 0, "1")]
    [InlineData("A", -1, "1")]
    [InlineData("A", 1, "-0.01")]
    public void Total_WithInvalidLine_ThrowsArgumentException(string? sku, int quantity, string unitPrice)
    {
        List<InvoiceLine> lines = new List<InvoiceLine> { new InvoiceLine(sku!, quantity, ParseDecimal(unitPrice)) };

        Assert.ThrowsAny<ArgumentException>(() => InvoiceCalculator.Total(lines, 0m));
    }

    [Theory]
    [InlineData("-0.01")]
    [InlineData("100.01")]
    public void Total_WithDiscountOutOfRange_ThrowsArgumentOutOfRangeException(string discountPercent)
    {
        List<InvoiceLine> lines = new List<InvoiceLine> { new InvoiceLine("A", 1, 1m) };

        Assert.Throws<ArgumentOutOfRangeException>(() => InvoiceCalculator.Total(lines, ParseDecimal(discountPercent)));
    }

    private static decimal ParseDecimal(string text)
    {
        return decimal.Parse(text, System.Globalization.CultureInfo.InvariantCulture);
    }
}
