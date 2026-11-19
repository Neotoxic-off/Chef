import charts


def test_versus_chart_is_an_svg_with_an_accessible_label() -> None:
    svg: str = charts.versus_chart(charts.LIGHT)

    assert svg.startswith("<svg")
    assert 'role="img"' in svg
    assert "Python CLI" in svg


def test_dark_theme_uses_dark_ink() -> None:
    svg: str = charts.seats_chart(charts.DARK)

    assert charts.DARK.ink in svg
    assert charts.LIGHT.ink not in svg
