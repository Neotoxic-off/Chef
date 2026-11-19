"""Render the README benchmark charts as light and dark SVGs into assets/bench.

The numbers come from bench/results/summary.json, written by report.py after a run; the cost split
is from one traced run (see the README). Run `python bench/charts.py`.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OUT: Path = Path(__file__).resolve().parent.parent / "assets" / "bench"
SUMMARY: Path = Path(__file__).resolve().parent / "results" / "summary.json"
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
    x: float = WIDTH - LEGEND_SPACING * len(entries)
    for color, name in entries:
        parts += [rect(x, y - 11, 14, 14, color), text(x + 22, y, name, theme.muted)]
        x += LEGEND_SPACING
    return parts


TASK_NAMES: dict[str, str] = {
    "bugfix": "Bug fix (TS)",
    "csharp": "C# library",
    "docker": "Dockerfile + compose",
    "github-actions": "GitHub Actions",
    "go": "Go package",
    "helm": "Helm chart",
    "java": "Java library",
    "prometheus": "Prometheus",
    "python": "Python CLI",
    "refactor": "Refactor (Python)",
    "rust": "Rust crate",
    "terraform": "Terraform module",
    "typescript": "TypeScript module",
}
ARM_NAMES: dict[str, str] = {"none": "Plain Claude", "control": "Control: AGENTS.md", "chef": "Chef 1.0"}
ROW_HEIGHT: float = 14.0
BAR_HEIGHT: float = 9.0
BAR_GAP: float = 5.0
LEGEND_SPACING: float = 175.0
LABEL_WIDTH: float = 180.0
VALUE_WIDTH: float = 70.0
SPLIT: list[tuple[str, str, int]] = [
    ("Cache writes", "new context: prompt, skill, tool output", 57),
    ("Output", "code, tests, configs", 28),
    ("Cache reads", "re-read each call", 15),
]


def arm_colors(theme: Theme) -> dict[str, str]:
    return {"none": theme.without, "control": theme.old, "chef": theme.chef}


@dataclass(frozen=True)
class Series:
    key: str
    name: str
    color: str


@dataclass(frozen=True)
class Chart:
    title: str
    label: str
    top: float
    unit: str


def rows_chart(theme: Theme, chart: Chart, rows: list[tuple[str, dict[str, float]]], series: list[Series]) -> str:
    """One row per task, one thin bar per series; values are printed next to each bar."""
    body: list[str] = [text(0, 26, chart.title, theme.ink, 18, 600)]
    body += legend(theme, 26, [(entry.color, entry.name) for entry in series])
    bar_width: float = WIDTH - LABEL_WIDTH - VALUE_WIDTH
    y: float = 56.0
    for name, values in rows:
        block_height: float = len(series) * (BAR_HEIGHT + BAR_GAP) - BAR_GAP
        body += [text(0, y + block_height / 2 + 5, TASK_NAMES.get(name, name), theme.ink, 14, 600)]
        for index, entry in enumerate(series):
            value: float = values.get(entry.key, 0.0)
            bar_y: float = y + index * (BAR_HEIGHT + BAR_GAP)
            shown: str = f"${value:.3f}" if chart.unit == "$" else f"{value:.0f}%"
            body += [rect(LABEL_WIDTH, bar_y, bar_width, BAR_HEIGHT, theme.track)]
            body += [rect(LABEL_WIDTH, bar_y, max(bar_width * value / chart.top, 1.0), BAR_HEIGHT, entry.color)]
            body += [text(LABEL_WIDTH + bar_width + 8, bar_y + BAR_HEIGHT, shown, theme.muted, 12)]
        y += ROW_HEIGHT + block_height
    return svg(int(y), chart.label, body)


def cost_chart(theme: Theme, summary: dict[str, Any]) -> str:
    colors: dict[str, str] = arm_colors(theme)
    series: list[Series] = [Series(arm, ARM_NAMES[arm], colors[arm]) for arm in ("none", "control", "chef")]
    tasks: list[str] = sorted(summary["tasks"]["chef"])
    rows: list[tuple[str, dict[str, float]]] = [
        (task, {arm: summary["tasks"][arm][task]["cost_usd"] or 0.0 for arm in ARM_NAMES}) for task in tasks
    ]
    top: float = max(value for _, values in rows for value in values.values())
    label: str = "Median cost per task, " + "; ".join(
        f"{task}: " + ", ".join(f"{ARM_NAMES[arm]} ${values[arm]:.3f}" for arm in ARM_NAMES) for task, values in rows
    )
    return rows_chart(theme, Chart("Median cost per task (USD)", label, top, "$"), rows, series)


def win_rate(counts: dict[str, float]) -> float:
    decided: float = counts["b"] + counts["a"] + counts["tie"]
    return 100 * (counts["b"] + counts["tie"] / 2) / decided if decided else 0.0


def pairwise_chart(theme: Theme, summary: dict[str, Any]) -> str:
    comparisons: dict[str, Series] = {
        "chef_vs_none": Series("chef_vs_none", "Chef vs plain Claude", theme.chef),
        "chef_vs_control": Series("chef_vs_control", "Chef vs control", theme.old),
    }
    present: list[Series] = [entry for key, entry in comparisons.items() if key in summary["pairwise"]]
    tasks: list[str] = sorted(summary["tasks"]["chef"])
    rows: list[tuple[str, dict[str, float]]] = [
        (
            task,
            {
                entry.key: win_rate(summary["pairwise"][entry.key]["per_task"].get(task, {"b": 0, "a": 0, "tie": 1}))
                for entry in present
            },
        )
        for task in tasks
    ]
    label: str = "Blind pairwise win rate of chef per task, ties count half: " + "; ".join(
        f"{task}: " + ", ".join(f"{entry.name} {values[entry.key]:.0f}%" for entry in present) for task, values in rows
    )
    title: str = "Blind reviewers prefer chef's version (win rate, ties = half)"
    return rows_chart(theme, Chart(title, label, 100.0, "%"), rows, present)


OVERVIEW_PANELS: tuple[tuple[str, str], ...] = (
    ("Would merge as is (blind review)", "merge"),
    ("Changes required (fewer is better)", "major"),
    ("Median cost per task", "cost"),
)
PANEL_WIDTH: float = 150.0
PANEL_STEP: float = 230.0


def overview_values(summary: dict[str, Any], arm: str) -> dict[str, float]:
    review: dict[str, float] = summary["reviews"][arm]
    return {
        "merge": 100 * review["merge_as_is"],
        "major": review["major_changes"],
        "cost": summary["overall"][arm]["median_cost_usd"],
    }


def overview_cell(theme: Theme, x: float, y: float, value: float, scale: tuple[float, str, str]) -> list[str]:
    top, unit, color = scale
    shown: str = {"%": f"{value:.0f}%", "$": f"${value:.3f}", "": f"{value:.2f}"}[unit]
    return [
        rect(x, y, PANEL_WIDTH, 16, theme.track),
        rect(x, y, max(PANEL_WIDTH * value / top, 1.0), 16, color),
        text(x + PANEL_WIDTH + 8, y + 13, shown, theme.ink, 13, 600),
    ]


def overview_chart(theme: Theme, summary: dict[str, Any]) -> str:
    """Headline chart: each arm on the three numbers a reader decides on."""
    arms: list[str] = [arm for arm in ARM_NAMES if arm in summary["reviews"]]
    values: dict[str, dict[str, float]] = {arm: overview_values(summary, arm) for arm in arms}
    tops: dict[str, tuple[float, str]] = {
        "merge": (100.0, "%"),
        "major": (max(values[arm]["major"] for arm in arms), ""),
        "cost": (max(values[arm]["cost"] for arm in arms), "$"),
    }
    body: list[str] = [text(0, 26, "Same tasks, same model: what each setup gives you", theme.ink, 18, 600)]
    for index, (title, _) in enumerate(OVERVIEW_PANELS):
        body += [text(LABEL_WIDTH + index * PANEL_STEP, 62, title, theme.muted, 13, 600)]
    colors: dict[str, str] = arm_colors(theme)
    y: float = 80.0
    for arm in arms:
        body += [text(0, y + 13, ARM_NAMES[arm], theme.ink, 15, 600)]
        for index, (_, key) in enumerate(OVERVIEW_PANELS):
            top, unit = tops[key]
            body += overview_cell(theme, LABEL_WIDTH + index * PANEL_STEP, y, values[arm][key], (top, unit, colors[arm]))
        y += 34
    label: str = "; ".join(
        f"{ARM_NAMES[arm]}: merged as is {values[arm]['merge']:.0f}%, {values[arm]['major']:.2f} changes required per review, "
        f"median cost ${values[arm]['cost']:.3f} per task"
        for arm in arms
    )
    return svg(int(y + 6), label, body)


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
    summary: dict[str, Any] = json.loads(SUMMARY.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in (LIGHT, DARK):
        (OUT / f"overview{theme.suffix}.svg").write_text(overview_chart(theme, summary), encoding="utf-8")
        (OUT / f"cost{theme.suffix}.svg").write_text(cost_chart(theme, summary), encoding="utf-8")
        (OUT / f"pairwise{theme.suffix}.svg").write_text(pairwise_chart(theme, summary), encoding="utf-8")
        (OUT / f"cost-split{theme.suffix}.svg").write_text(split_chart(theme), encoding="utf-8")


if __name__ == "__main__":
    main()
