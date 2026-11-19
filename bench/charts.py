"""Render the README benchmark charts as light and dark SVGs into assets/bench.

The numbers are copied from score.py and blind_review.py summaries; update them after a new run,
then run `python bench/charts.py`.
"""

from dataclasses import dataclass
from pathlib import Path

OUT: Path = Path(__file__).resolve().parent.parent / "assets" / "bench"
FONT: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
WIDTH: int = 880


@dataclass(frozen=True)
class Theme:
    suffix: str
    ink: str
    muted: str
    track: str
    without: str
    old: str
    chef: str


LIGHT: Theme = Theme("", "#1F2328", "#59636E", "#E6E8EB", "#C9CED6", "#EDB59F", "#D97757")
DARK: Theme = Theme("-dark", "#E6EDF3", "#9198A1", "#30363D", "#4A5059", "#8A4A35", "#D97757")


def text(x: float, y: float, value: str, fill: str, size: int = 13, weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{value}</text>'
    )


def rect(x: float, y: float, width: float, height: float, fill: str) -> str:
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="3" fill="{fill}"/>'


def svg(height: int, label: str, body: list[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
        f'role="img" aria-label="{label}"><title>{label}</title>{"".join(body)}</svg>\n'
    )


def legend(theme: Theme, y: float, entries: list[tuple[str, str]]) -> list[str]:
    parts: list[str] = []
    x: float = WIDTH - 130.0 * len(entries)
    for color, name in entries:
        parts += [rect(x, y - 11, 14, 14, color), text(x + 22, y, name, theme.muted)]
        x += 130
    return parts


SCORECARD: list[tuple[str, str, int, int]] = [
    ("Correct", "hidden test and promtool pass", 100, 100),
    ("Tested", "Python: tests written", 0, 100),
    ("Covered", "Python: line coverage ≥ 90%", 0, 100),
    ("Typed", "Python: mypy --strict clean", 0, 100),
    ("Strict tooling", "Ruff + strict type checker configured", 0, 100),
    ("Rule tests", "Prometheus: promtool test rules pass", 0, 100),
    ("Runbooks", "Prometheus: runbook_url on every alert", 0, 100),
    ("Pinned image", "Prometheus image pinned", 0, 100),
    ("Resource limits", "Docker compose limits set", 80, 100),
]


def scorecard(theme: Theme) -> str:
    label: str = "Share of runs that meet each check, without chef and with chef 0.10.0, 5 runs each"
    body: list[str] = [text(0, 26, "Share of runs that meet each check", theme.ink, 18, 600)]
    body += legend(theme, 26, [(theme.without, "Without chef"), (theme.chef, "Chef 0.10.0")])
    bar_x: float = 300.0
    bar_width: float = 480.0
    y: float = 64.0
    for name, detail, without, chef in SCORECARD:
        body += [text(0, y + 12, name, theme.ink, 15, 600), text(0, y + 32, detail, theme.muted, 12)]
        for offset, value, color, ink, weight in (
            (0, without, theme.without, theme.muted, 400),
            (20, chef, theme.chef, theme.ink, 600),
        ):
            body += [rect(bar_x, y + offset, bar_width, 14, theme.track)]
            if value:
                body += [rect(bar_x, y + offset, bar_width * value / 100, 14, color)]
            body += [text(bar_x + bar_width + 12, y + offset + 12, f"{value}%", ink, 13, weight)]
        y += 58
    return svg(int(y), label, body)


COSTS: list[tuple[str, float, float, float]] = [
    ("Python CLI", 0.060, 0.211, 0.192),
    ("Dockerfile + compose", 0.051, 0.128, 0.128),
    ("Prometheus", 0.081, 0.189, 0.183),
]
COST_MAX: float = 0.25


def grouped_chart(
    theme: Theme, title: str, label: str, rows: list[tuple[str, float, float, float]], top: float, unit: str
) -> str:
    body: list[str] = [text(0, 26, title, theme.ink, 18, 600)]
    body += legend(theme, 26, [(theme.without, "Without chef"), (theme.old, "Chef 0.9.0"), (theme.chef, "Chef 0.10.0")])
    base_y: float = 300.0
    plot_height: float = 220.0
    group_width: float = WIDTH / len(rows)
    bar_width: float = 56.0
    body += [f'<line x1="0" y1="{base_y}" x2="{WIDTH}" y2="{base_y}" stroke="{theme.track}"/>']
    colors: tuple[str, str, str] = (theme.without, theme.old, theme.chef)
    for index, (task, *values) in enumerate(rows):
        center: float = group_width * index + group_width / 2
        for slot, (value, color) in enumerate(zip(values, colors, strict=True)):
            x: float = center + (slot - 1.5) * (bar_width + 4) + 2
            height: float = plot_height * value / top
            shown: str = f"${value:.3f}" if unit == "$" else f"{value:.0f}%"
            ink: str = theme.ink if slot == 2 else theme.muted
            body += [rect(x, base_y - height, bar_width, height, color)]
            body += [text(x + bar_width / 2, base_y - height - 8, shown, ink, 13, 600 if slot == 2 else 400, "middle")]
        body += [text(center, base_y + 24, task, theme.ink, 14, 600, "middle")]
    return svg(330, label, body)


def cost_chart(theme: Theme) -> str:
    label: str = (
        "Median cost per task over 5 runs. Python: $0.060 without chef, $0.211 chef 0.9.0, $0.192 chef 0.10.0. "
        "Docker: $0.051, $0.128, $0.128. Prometheus: $0.081, $0.189, $0.183."
    )
    return grouped_chart(theme, "Median cost per task (USD, 5 runs)", label, COSTS, COST_MAX, "$")


QUALITY: list[tuple[str, float, float, float]] = [
    ("Python CLI", 27, 90, 97),
    ("Dockerfile + compose", 85, 92, 92),
    ("Prometheus", 70, 100, 100),
]


def quality_chart(theme: Theme) -> str:
    label: str = (
        "Checks chef enforces, share passed per task, mean over 5 runs. Python: 27% without chef, 90% chef 0.9.0, "
        "97% chef 0.10.0. Docker: 85%, 92%, 92%. Prometheus: 70%, 100%, 100%."
    )
    return grouped_chart(theme, "Checks chef enforces, share passed (5 runs)", label, QUALITY, 110, "%")


VERSUS: list[tuple[str, tuple[float, float], tuple[float, float], tuple[float, float]]] = [
    ("Python CLI", (0.060, 0.192), (7.4, 8.1), (30, 65)),
    ("Dockerfile + compose", (0.051, 0.128), (8.0, 7.9), (80, 70)),
    ("Prometheus", (0.081, 0.183), (6.85, 7.5), (10, 25)),
]
PANEL_WIDTH: float = 150.0


def versus_panel(theme: Theme, x0: float, y: float, values: tuple[float, float], top: float, unit: str) -> list[str]:
    parts: list[str] = []
    for offset, value, color, ink, weight in (
        (0, values[0], theme.without, theme.muted, 400),
        (20, values[1], theme.chef, theme.ink, 600),
    ):
        shown: str = {"$": f"${value:.3f}", "/10": f"{value:.2f}", "%": f"{value:.0f}%"}[unit]
        parts += [rect(x0, y + offset, PANEL_WIDTH, 14, theme.track), rect(x0, y + offset, PANEL_WIDTH * value / top, 14, color)]
        parts += [text(x0 + PANEL_WIDTH + 8, y + offset + 12, shown, ink, 13, weight)]
    return parts


def versus_chart(theme: Theme) -> str:
    label: str = (
        "Without chef versus with chef 0.10.0, per task over 5 runs: median cost, blind panel quality score out of 10, "
        "and share of blind reviews that would merge as is. Python CLI: $0.060, 7.4, 30% versus $0.192, 8.1, 65%. "
        "Dockerfile and compose: $0.051, 8.0, 80% versus $0.128, 7.9, 70%. Prometheus: $0.081, 6.85, 10% versus $0.183, 7.5, 25%."
    )
    body: list[str] = [text(0, 26, "Without vs with chef: cost and blind review", theme.ink, 18, 600)]
    body += legend(theme, 26, [(theme.without, "Without chef"), (theme.chef, "Chef 0.10.0")])
    columns: tuple[tuple[float, str, float, str], ...] = (
        (190.0, "Cost per task (median)", COST_MAX, "$"),
        (420.0, "Quality, blind panel (/10)", 10.0, "/10"),
        (650.0, "Would merge as is", 100.0, "%"),
    )
    for x, title, _, _ in columns:
        body += [text(x, 64, title, theme.muted, 13, 600)]
    y: float = 84.0
    for task, *values in VERSUS:
        body += [text(0, y + 22, task, theme.ink, 15, 600)]
        for (x, _, top, unit), pair in zip(columns, values, strict=True):
            body += versus_panel(theme, x, y, pair, top, unit)
        y += 58
    return svg(int(y), label, body)


def paired_rows_chart(
    theme: Theme, title: str, label: str, rows: list[tuple[str, str, float, float]], top: float, unit: str
) -> str:
    body: list[str] = [text(0, 26, title, theme.ink, 18, 600)]
    body += legend(theme, 26, [(theme.without, "Without chef"), (theme.chef, "Chef 0.10.0")])
    bar_x: float = 300.0
    bar_width: float = 480.0
    y: float = 64.0
    for name, detail, without, chef in rows:
        body += [text(0, y + 12, name, theme.ink, 15, 600), text(0, y + 32, detail, theme.muted, 12)]
        for offset, value, color, ink, weight in (
            (0, without, theme.without, theme.muted, 400),
            (20, chef, theme.chef, theme.ink, 600),
        ):
            shown: str = f"{value:.2f}" if unit == "" else f"{value:.2f}{unit}"
            body += [
                rect(bar_x, y + offset, bar_width, 14, theme.track),
                rect(bar_x, y + offset, bar_width * value / top, 14, color),
            ]
            body += [text(bar_x + bar_width + 12, y + offset + 12, shown, ink, 13, weight)]
        y += 58
    return svg(int(y), label, body)


MAJOR_CHANGES: list[tuple[str, str, float, float]] = [
    ("Python CLI", "20 reviews per arm", 1.25, 0.40),
    ("Dockerfile + compose", "20 reviews per arm", 0.25, 0.35),
    ("Prometheus", "20 reviews per arm", 1.85, 1.25),
    ("All tasks", "60 reviews per arm", 1.12, 0.67),
]
SEATS: list[tuple[str, str, float, float]] = [
    ("Senior engineer", "design and correctness", 7.53, 7.80),
    ("Security reviewer", "what an attacker or a mistake could exploit", 7.47, 8.07),
    ("SRE", "deploys it, gets paged when it breaks", 7.20, 7.53),
    ("Maintainer", "owns and changes it for two years", 7.47, 7.93),
]


def majors_chart(theme: Theme) -> str:
    label: str = (
        "Blind panel: 'should fix before merge' changes requested per review, without chef versus chef 0.10.0. "
        "Python 1.25 vs 0.40, Docker 0.25 vs 0.35, Prometheus 1.85 vs 1.25, all tasks 1.12 vs 0.67."
    )
    return paired_rows_chart(
        theme, "Blind panel: 'should fix' changes per review (lower is better)", label, MAJOR_CHANGES, 2.0, ""
    )


def seats_chart(theme: Theme) -> str:
    label: str = (
        "Blind panel quality score out of 10 by reviewer seat, without chef versus chef 0.10.0, 15 reviews each. "
        "Senior 7.53 vs 7.80, security 7.47 vs 8.07, SRE 7.20 vs 7.53, maintainer 7.47 vs 7.93."
    )
    return paired_rows_chart(theme, "Blind panel: quality by reviewer seat (/10)", label, SEATS, 10.0, "")


SPLIT: list[tuple[str, str, int]] = [
    ("Cache writes", "new context: prompt, skill, tool output", 57),
    ("Output", "code, tests, configs", 28),
    ("Cache reads", "re-read each call", 15),
]


def split_chart(theme: Theme) -> str:
    label: str = "Where one chef run's cost goes: cache writes 57%, output 28%, cache reads 15%"
    body: list[str] = [text(0, 26, "Where the cost of a chef run goes", theme.ink, 18, 600)]
    colors: tuple[str, str, str] = (theme.chef, theme.old, theme.without)
    x: float = 0.0
    for (name, detail, share), color in zip(SPLIT, colors, strict=True):
        width: float = WIDTH * share / 100
        body += [rect(x, 48, width - 2, 28, color)]
        body += [text(x, 100, f"{name} {share}%", theme.ink, 14, 600), text(x, 118, detail, theme.muted, 12)]
        x += width
    return svg(130, label, body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in (LIGHT, DARK):
        (OUT / f"scorecard{theme.suffix}.svg").write_text(scorecard(theme), encoding="utf-8")
        (OUT / f"cost{theme.suffix}.svg").write_text(cost_chart(theme), encoding="utf-8")
        (OUT / f"versus{theme.suffix}.svg").write_text(versus_chart(theme), encoding="utf-8")
        (OUT / f"panel-majors{theme.suffix}.svg").write_text(majors_chart(theme), encoding="utf-8")
        (OUT / f"panel-seats{theme.suffix}.svg").write_text(seats_chart(theme), encoding="utf-8")
        (OUT / f"quality{theme.suffix}.svg").write_text(quality_chart(theme), encoding="utf-8")
        (OUT / f"cost-split{theme.suffix}.svg").write_text(split_chart(theme), encoding="utf-8")


if __name__ == "__main__":
    main()
