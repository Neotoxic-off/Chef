"""Render the README benchmark charts as light and dark SVGs into assets/bench.

The numbers come from bench/results/summary.json, written by report.py after a run; the cost split
is from one traced run (see the README). Run `python bench/charts.py`.
"""

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OUT: Path = Path(__file__).resolve().parent.parent / "assets" / "bench"
SUMMARY: Path = Path(__file__).resolve().parent / "results" / "summary.json"
HISTORY: Path = Path(__file__).resolve().parent / "results" / "history.json"
STACKS: Path = Path(__file__).resolve().parent / "results" / "merge-stacks.json"
MERGE: Path = Path(__file__).resolve().parent / "results" / "merge.json"
QUALITY: Path = Path(__file__).resolve().parent / "results" / "quality.json"
MERGE_15: Path = Path(__file__).resolve().parent / "results" / "merge-15.json"
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
    # The chef before the previous one, lighter than `old`.
    older: str


LIGHT: Theme = Theme("", "#1F2328", "#59636E", "#E6E8EB", "#C9CED6", "#EDB59F", "#D97757", "#F6D9CD")
DARK: Theme = Theme("-dark", "#E6EDF3", "#9198A1", "#30363D", "#4A5059", "#8A4A35", "#D97757", "#5C3427")


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
    "sql": "SQL migration",
    "bash": "Bash script",
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


ROW_SHOWN: dict[str, str] = {"$": "${value:.3f}", "%": "{value:.0f}%", "/10": "{value:.1f}"}


def rows_chart(theme: Theme, chart: Chart, rows: list[tuple[str, dict[str, float]]], series: list[Series]) -> str:
    """One row per task, one thin bar per series; values are printed next to each bar."""
    body: list[str] = [text(0, 26, chart.title, theme.ink, 18, 600)]
    # Under the title, not beside it: a long title would run into the legend.
    body += legend(theme, 54, [(entry.color, entry.name) for entry in series])
    bar_width: float = WIDTH - LABEL_WIDTH - VALUE_WIDTH
    y: float = 82.0
    for name, values in rows:
        block_height: float = len(series) * (BAR_HEIGHT + BAR_GAP) - BAR_GAP
        body += [text(0, y + block_height / 2 + 5, TASK_NAMES.get(name, name), theme.ink, 14, 600)]
        for index, entry in enumerate(series):
            value: float = values.get(entry.key, 0.0)
            bar_y: float = y + index * (BAR_HEIGHT + BAR_GAP)
            shown: str = ROW_SHOWN[chart.unit].format(value=value)
            body += [rect(LABEL_WIDTH, bar_y, bar_width, BAR_HEIGHT, theme.track)]
            body += [rect(LABEL_WIDTH, bar_y, max(bar_width * value / chart.top, 1.0), BAR_HEIGHT, entry.color)]
            body += [text(LABEL_WIDTH + bar_width + 8, bar_y + BAR_HEIGHT, shown, theme.muted, 12)]
        y += ROW_HEIGHT + block_height
    return svg(int(y), chart.label, body)


QUALITY_ARMS: tuple[tuple[str, str], ...] = (("none", "Without chef"), ("chef15", "With chef 1.5"))
QUALITY_NAMES: dict[str, str] = {
    "aspnetcore": "ASP.NET Core", "bash": "Bash", "c": "C", "ci": "GitHub Actions", "cpp": "C++", "csharp": "C#",
    "django": "Django", "docker": "Docker", "fastapi": "FastAPI", "go": "Go", "java": "Java", "kotlin": "Kotlin",
    "kubernetes": "Kubernetes", "laravel": "Laravel", "mongodb": "MongoDB", "nextjs": "Next.js", "php": "PHP",
    "postgres": "PostgreSQL", "powershell": "PowerShell", "python": "Python", "rails": "Rails", "react": "React",
    "redis": "Redis", "ruby": "Ruby", "rust": "Rust", "spring-boot": "Spring Boot", "sql": "SQL", "swift": "Swift",
    "terraform": "Terraform", "typescript": "TypeScript", "vue": "Vue", "angular": "Angular",
}  # fmt: skip


ICONS: Path = Path(__file__).resolve().parent / "icons.json"
# Simple Icons has no C#, PowerShell or plain SQL logo: those tiles show these letters instead.
MONOGRAMS: dict[str, str] = {"csharp": "C#", "powershell": "PS", "sql": "SQL"}
TILE_COLUMNS: int = 4
TILE_WIDTH: float = WIDTH / TILE_COLUMNS
TILE_HEIGHT: float = 64.0
TILES_TOP: float = 132.0


def icon(theme: Theme, x: float, y: float, task: str, paths: dict[str, str]) -> list[str]:
    if task in paths:
        return [f'<path transform="translate({x:.1f} {y:.1f})" d="{paths[task]}" fill="{theme.ink}"/>']
    return [text(x + 12, y + 17, MONOGRAMS.get(task, task[:3].upper()), theme.ink, 12, 700, "middle")]


def quality_tile(theme: Theme, origin: tuple[float, float], name: str, scores: tuple[float, float]) -> list[str]:
    x, y = origin
    without, with_chef = scores
    return [
        text(x + 34, y + 10, name, theme.ink, 14, 600),
        text(x + 34, y + 32, f"{without:.1f}", theme.muted, 14),
        text(x + 66, y + 32, "→", theme.muted, 14),
        text(x + 86, y + 32, f"{with_chef:.1f}", theme.chef, 15, 700),
        text(x + 122, y + 32, f"{with_chef - without:+.1f}", theme.chef, 13, 600),
    ]


def quality_chart(theme: Theme, quality: dict[str, Any]) -> str:
    """One tile per language: its icon, the score without chef, then with chef 1.5; biggest gain first."""
    paths: dict[str, str] = json.loads(ICONS.read_text(encoding="utf-8"))["paths"]
    criteria: list[str] = quality["criteria"]
    mean: dict[str, float] = {
        arm: statistics.fmean(quality["arms"][arm][name] for name in criteria) for arm in ("none", "chef15")
    }
    tasks: list[tuple[str, dict[str, float]]] = sorted(
        quality["tasks"].items(), key=lambda item: item[1]["chef15"] - item[1]["none"], reverse=True
    )
    body: list[str] = [
        text(0, 26, "Code quality per language, without chef → with chef 1.5", theme.ink, 18, 600),
        text(0, 50, f"0 to 10 from a blind reviewer: the mean of {', '.join(criteria)}", theme.muted, 13),
        text(0, 92, f"All {len(tasks)} languages", theme.ink, 16, 600),
        *quality_tile(theme, (150.0, 70.0), "", (mean["none"], mean["chef15"])),
    ]
    for index, (task, scores) in enumerate(tasks):
        x: float = (index % TILE_COLUMNS) * TILE_WIDTH
        y: float = TILES_TOP + (index // TILE_COLUMNS) * TILE_HEIGHT
        body += icon(theme, x, y + 2, task, paths)
        body += quality_tile(theme, (x, y + 8), QUALITY_NAMES.get(task, task), (scores["none"], scores["chef15"]))
    rows: int = -(-len(tasks) // TILE_COLUMNS)
    label: str = (
        f"Code quality per language, 0 to 10, without chef then with chef 1.5. All: {mean['none']:.1f} to {mean['chef15']:.1f}. "
        + "; ".join(f"{QUALITY_NAMES.get(task, task)} {scores['none']:.1f} to {scores['chef15']:.1f}" for task, scores in tasks)
    )
    return svg(int(TILES_TOP + rows * TILE_HEIGHT), label, body)


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
    ("First answer accepted", "merge"),
    ("Review rounds, share of tasks", "major"),
    ("Cost per task, fixes included", "cost"),
)
# The newest chef arm is the one the break-even chart and the README headline compare with plain Claude.
# The break-even and time charts compare these two on the latest bench (results/merge-15.json).
LATEST_CHEF: tuple[str, str] = ("chef15", "Chef 1.5")
PREVIOUS_CHEF: tuple[str, str] = ("chef14", "Chef 1.4")
# The 13-task bench (results/merge.json), every arm reviewed with the 1.2 loop.
OVERVIEW_ARMS: dict[str, str] = {"none": "Plain Claude", "chef13": "Chef 1.3", "chef14": "Chef 1.4", "chef15": "Chef 1.5"}
PANEL_WIDTH: float = 150.0
PANEL_STEP: float = 230.0


def overview_values(merge: dict[str, dict[str, float]], arm: str) -> dict[str, float]:
    loop: dict[str, float] = merge[arm]
    return {
        "merge": 100 * loop["merged_first_time"],
        "major": 100 * loop["fix_rounds_per_run"],
        "cost": loop["total_cost"] / loop["runs"],
    }


def overview_cell(theme: Theme, x: float, y: float, value: float, scale: tuple[float, str, str]) -> list[str]:
    top, unit, color = scale
    shown: str = {"%": f"{value:.0f}%", "$": f"${value:.3f}"}[unit]
    return [
        rect(x, y, PANEL_WIDTH, 16, theme.track),
        rect(x, y, max(PANEL_WIDTH * value / top, 1.0), 16, color),
        text(x + PANEL_WIDTH + 8, y + 13, shown, theme.ink, 13, 600),
    ]


OVERVIEW_TITLE: str = "Same 13 tasks, same model, a blind reviewer asks for fixes until it merges"
STACKS_ARMS: dict[str, str] = {"none": "Plain Claude", "chef14": "Chef 1.4"}
STACKS_TITLE: str = "Most-used stacks, 9 tasks: Node, React, Bash, SQL, PHP, PowerShell, C, C++, Kotlin"
RELEASE_15_ARMS: dict[str, str] = {"none": "Plain Claude", "chef14": "Chef 1.4", "chef15": "Chef 1.5"}
RELEASE_15_TITLE: str = "Chef 1.5 bench: 11 tasks, 3 of them held out, 95 runs per arm"


def arm_shades(theme: Theme, arms: list[str]) -> dict[str, str]:
    """Plain Claude in grey; the newest chef in the chef color, the one before it lighter, older ones lighter still."""
    chefs: list[str] = [arm for arm in arms if arm != "none"]
    shades: list[str] = [theme.chef, theme.old]
    return {"none": theme.without} | {
        arm: shades[age] if age < len(shades) else theme.older for age, arm in enumerate(reversed(chefs))
    }


def overview_chart(
    theme: Theme, merge: dict[str, dict[str, float]], title: str = OVERVIEW_TITLE, names: dict[str, str] = OVERVIEW_ARMS
) -> str:
    """Headline chart: each arm on the three numbers a reader decides on, from the review-and-fix loop."""
    arms: list[str] = [arm for arm in names if arm in merge]
    values: dict[str, dict[str, float]] = {arm: overview_values(merge, arm) for arm in arms}
    tops: dict[str, tuple[float, str]] = {
        "merge": (100.0, "%"),
        "major": (max(values[arm]["major"] for arm in arms), "%"),
        "cost": (max(values[arm]["cost"] for arm in arms), "$"),
    }
    body: list[str] = [text(0, 26, title, theme.ink, 18, 600)]
    for index, (panel_title, _) in enumerate(OVERVIEW_PANELS):
        body += [text(LABEL_WIDTH + index * PANEL_STEP, 62, panel_title, theme.muted, 13, 600)]
    colors: dict[str, str] = arm_shades(theme, arms)
    y: float = 80.0
    for arm in arms:
        body += [text(0, y + 13, names[arm], theme.ink, 15, 600)]
        for index, (_, key) in enumerate(OVERVIEW_PANELS):
            top, unit = tops[key]
            body += overview_cell(theme, LABEL_WIDTH + index * PANEL_STEP, y, values[arm][key], (top, unit, colors[arm]))
        y += 34
    label: str = "; ".join(
        f"{names[arm]}: first answer accepted {values[arm]['merge']:.0f}%, {values[arm]['major']:.0f} review rounds per 100 tasks, "
        f"${values[arm]['cost']:.3f} per task with fixes"
        for arm in arms
    )
    return svg(int(y + 6), label, body)


HISTORY_PANEL_WIDTH: float = 330.0
HISTORY_PANEL_HEIGHT: float = 150.0
HISTORY_PANEL_GAP: float = 120.0
HISTORY_TOP: float = 70.0
HISTORY_WIDE_WIDTH: float = 760.0


@dataclass(frozen=True)
class Panel:
    x: float
    title: str
    key: str
    top: float
    unit: str
    width: float = HISTORY_PANEL_WIDTH


def history_point(panel: Panel, index: int, count: int, value: float) -> tuple[float, float]:
    step: float = panel.width / max(count - 1, 1)
    return panel.x + index * step, HISTORY_TOP + HISTORY_PANEL_HEIGHT * (1 - value / panel.top)


def same_reviewer_segments(versions: list[dict[str, Any]], points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Points to join with a line: consecutive versions judged by the same reviewer, so a reviewer change shows as a gap."""
    segments: list[list[tuple[float, float]]] = []
    previous: str | None = None
    for entry, point in zip(versions, points, strict=True):
        reviewer: str | None = entry.get("reviewer")
        if not segments or reviewer != previous:
            segments.append([])
        segments[-1].append(point)
        previous = reviewer
    return segments


HISTORY_SHOWN: dict[str, str] = {"$": "${:.3f}", "%": "{:.0f}%", "s": "{:.0f} s"}
REVIEWED_KEY: str = "merge"


def baseline_marks(theme: Theme, panel: Panel, history: dict[str, Any]) -> list[str]:
    """Plain Claude's dashed line; on the reviewed panel only while it shares the latest version's reviewer."""
    baseline: dict[str, Any] = history["baseline"]
    if panel.key == REVIEWED_KEY and baseline.get("reviewer") != history["versions"][-1].get("reviewer"):
        return []
    base_y: float = history_point(panel, 0, len(history["versions"]), baseline[panel.key])[1]
    baseline_line: str = (
        f'<line x1="{panel.x}" y1="{base_y:.1f}" x2="{panel.x + panel.width}" y2="{base_y:.1f}" '
        f'stroke="{theme.without}" stroke-width="2" stroke-dasharray="6 4"/>'
    )
    return [
        baseline_line,
        text(
            panel.x + panel.width,
            base_y - 6,
            "plain Claude " + HISTORY_SHOWN[panel.unit].format(baseline[panel.key]),
            theme.muted,
            11,
            400,
            "end",
        ),
    ]


def history_panel(theme: Theme, panel: Panel, history: dict[str, Any]) -> list[str]:
    versions: list[dict[str, Any]] = history["versions"]
    shown: dict[str, str] = HISTORY_SHOWN
    body: list[str] = [text(panel.x, HISTORY_TOP - 22, panel.title, theme.muted, 13, 600)]
    body += baseline_marks(theme, panel, history)
    points: list[tuple[float, float]] = [
        history_point(panel, index, len(versions), entry[panel.key]) for index, entry in enumerate(versions)
    ]
    segments: list[list[tuple[float, float]]] = (
        same_reviewer_segments(versions, points) if panel.key == REVIEWED_KEY else [points]
    )
    for segment in segments:
        body += [
            f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in segment)}" fill="none" stroke="{theme.chef}" stroke-width="2"/>'
        ]
    for (x, y), entry in zip(points, versions, strict=True):
        body += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{theme.chef}"/>']
        body += [text(x, y - 10, shown[panel.unit].format(entry[panel.key]), theme.ink, 12, 600, "middle")]
        body += [text(x, HISTORY_TOP + HISTORY_PANEL_HEIGHT + 22, entry["version"], theme.muted, 12, 400, "middle")]
    return body


HISTORY_METRICS: dict[str, tuple[str, str]] = {
    "cost": ("Chef across versions: cost per task (median)", "$"),
    "merge": ("Chef across versions: a blind reviewer would merge it as is", "%"),
}


def history_chart(theme: Theme, history: dict[str, Any], key: str) -> str:
    """One metric of chef by version, cost or blind-review quality, on the tasks every version ran."""
    title, unit = HISTORY_METRICS[key]
    values: list[float] = [entry[key] for entry in history["versions"]] + [history["baseline"][key]]
    top: float = 100.0 if unit == "%" else 1.2 * max(values)
    body: list[str] = [text(0, 26, title, theme.ink, 18, 600)]
    body += history_panel(theme, Panel(40.0, "", key, top, unit, HISTORY_WIDE_WIDTH), history)
    shown: str = HISTORY_SHOWN[unit]
    label: str = (
        f"{title}, on "
        + ", ".join(history["tasks"])
        + ": "
        + ", ".join(f"{entry['version']} {shown.format(entry[key])}" for entry in history["versions"])
        + f". Plain Claude: {shown.format(history['baseline'][key])}."
    )
    return svg(int(HISTORY_TOP + HISTORY_PANEL_HEIGHT + 40), label, body)


ROUND_COST_MAX: float = 20.0
ROUND_COST_EXAMPLE: float = 10.0
ROUND_COST_TICKS: tuple[float, ...] = (0.0, 5.0, 10.0, 15.0, 20.0)
PLOT_LEFT: float = 70.0
PLOT_RIGHT: float = 600.0
PLOT_TOP: float = 60.0
PLOT_BOTTOM: float = 230.0


def cost_with_reviews(loop: dict[str, float], round_cost: float) -> float:
    """Machine cost per task plus every review a human makes: the first one and one after each fix."""
    return loop["total_cost"] / loop["runs"] + (1 + loop["fix_rounds_per_run"]) * round_cost


def break_even(plain: dict[str, float], chef: dict[str, float]) -> float:
    extra_cost: float = chef["total_cost"] / chef["runs"] - plain["total_cost"] / plain["runs"]
    return extra_cost / (plain["fix_rounds_per_run"] - chef["fix_rounds_per_run"])


def plot_point(round_cost: float, cost: float, top: float) -> tuple[float, float]:
    x: float = PLOT_LEFT + (PLOT_RIGHT - PLOT_LEFT) * round_cost / ROUND_COST_MAX
    return x, PLOT_BOTTOM - (PLOT_BOTTOM - PLOT_TOP) * cost / top


def break_even_axes(theme: Theme, top: float) -> list[str]:
    body: list[str] = [
        f'<line x1="{PLOT_LEFT}" y1="{PLOT_BOTTOM}" x2="{PLOT_RIGHT}" y2="{PLOT_BOTTOM}" stroke="{theme.track}" stroke-width="1"/>'
    ]
    for tick in ROUND_COST_TICKS:
        x: float = plot_point(tick, 0.0, top)[0]
        body += [text(x, PLOT_BOTTOM + 18, f"${tick:.0f}", theme.muted, 11, 400, "middle")]
    body += [
        text((PLOT_LEFT + PLOT_RIGHT) / 2, PLOT_BOTTOM + 38, "Cost of one human review round", theme.muted, 12, 600, "middle")
    ]
    body += [text(PLOT_LEFT - 8, PLOT_TOP + 4, f"${top:.0f}", theme.muted, 11, 400, "end")]
    return body + [text(PLOT_LEFT - 8, PLOT_BOTTOM + 4, "$0", theme.muted, 11, 400, "end")]


def break_even_line(theme: Theme, loop: dict[str, float], color: str, top: float, label_left: bool = False) -> list[str]:
    start: tuple[float, float] = plot_point(0.0, cost_with_reviews(loop, 0.0), top)
    end: tuple[float, float] = plot_point(ROUND_COST_MAX, cost_with_reviews(loop, ROUND_COST_MAX), top)
    example: float = cost_with_reviews(loop, ROUND_COST_EXAMPLE)
    x, y = plot_point(ROUND_COST_EXAMPLE, example, top)
    return [
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" stroke="{color}" stroke-width="2.5"/>',
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>',
        text(x - 10, y + 4, f"${example:.2f}", theme.ink, 12, 600, "end")
        if label_left
        else text(x + 10, y + 4, f"${example:.2f}", theme.ink, 12, 600),
    ]


def break_even_chart(theme: Theme, merge: dict[str, dict[str, float]]) -> str:
    """When chef's extra machine cost is paid back by the review rounds it saves a human reviewer."""
    plain: dict[str, float] = merge["none"]
    chef: dict[str, float] = merge[LATEST_CHEF[0]]
    previous: dict[str, float] | None = merge.get(PREVIOUS_CHEF[0])
    loops: list[dict[str, float]] = [plain, chef] if previous is None else [plain, previous, chef]
    top: float = max(cost_with_reviews(loop, ROUND_COST_MAX) for loop in loops)
    threshold: float = break_even(plain, chef)
    saving: float = 1 - cost_with_reviews(chef, ROUND_COST_EXAMPLE) / cost_with_reviews(plain, ROUND_COST_EXAMPLE)
    body: list[str] = [text(0, 26, "Cost per task once the reviewer's time counts", theme.ink, 18, 600)]
    body += break_even_axes(theme, top)
    body += break_even_line(theme, plain, theme.without, top)
    notes: list[tuple[str, str]] = [(theme.without, f"Plain Claude: {1 + plain['fix_rounds_per_run']:.2f} reviews per task")]
    if previous is not None:
        body += break_even_line(theme, previous, theme.old, top, label_left=True)
        notes.append((theme.old, f"{PREVIOUS_CHEF[1]}: {1 + previous['fix_rounds_per_run']:.2f} reviews per task"))
    body += break_even_line(theme, chef, theme.chef, top)
    notes.append((theme.chef, f"{LATEST_CHEF[1]}: {1 + chef['fix_rounds_per_run']:.2f} reviews per task"))
    for index, (color, note) in enumerate(notes):
        body += [
            rect(PLOT_RIGHT + 20, PLOT_TOP + index * 24, 12, 12, color),
            text(PLOT_RIGHT + 38, PLOT_TOP + 11 + index * 24, note, theme.muted, 11),
        ]
    body += [
        text(PLOT_RIGHT + 20, PLOT_TOP + 94, f"Break-even: ${threshold:.2f} per round", theme.ink, 12, 600),
        text(
            PLOT_RIGHT + 20,
            PLOT_TOP + 114,
            f"At ${ROUND_COST_EXAMPLE:.0f} per round: {100 * saving:.0f}% less",
            theme.ink,
            12,
            600,
        ),
    ]
    label: str = (
        f"Machine cost per task plus a human reviewer's cost per review round. {LATEST_CHEF[1]} costs less once a round costs more than "
        f"${threshold:.2f}; at ${ROUND_COST_EXAMPLE:.0f} per round, plain Claude ${cost_with_reviews(plain, ROUND_COST_EXAMPLE):.2f} "
        f"and {LATEST_CHEF[1].lower()} ${cost_with_reviews(chef, ROUND_COST_EXAMPLE):.2f} per task, {100 * saving:.0f}% less."
    )
    return svg(int(PLOT_BOTTOM + 50), label, body)


TIME_ARMS: dict[str, str] = {
    "none": "Plain Claude",
    "chef11": "Chef 1.1",
    "chef12": "Chef 1.2",
    PREVIOUS_CHEF[0]: PREVIOUS_CHEF[1],
    LATEST_CHEF[0]: LATEST_CHEF[1],
}
TIME_STEPS: tuple[tuple[str, str], ...] = (
    ("first_answer_seconds", "First answer"),
    ("first_review_seconds", "First review"),
    ("back_and_forth_seconds", "Fixes and new reviews"),
)
TIME_LABEL_WIDTH: float = 95.0
TIME_BAR_WIDTH: float = 190.0
TIME_ROW_STEP: float = 36.0
TIME_LEGEND_STEP: float = 115.0


def time_colors(theme: Theme) -> tuple[str, str, str]:
    return theme.without, theme.old, theme.chef


def time_row(theme: Theme, y: float, steps: dict[str, float], top: float) -> list[str]:
    body: list[str] = []
    x: float = TIME_LABEL_WIDTH
    for (key, _), color in zip(TIME_STEPS, time_colors(theme), strict=True):
        width: float = TIME_BAR_WIDTH * steps[key] / top
        body += [rect(x, y, max(width - 1, 1.0), 20, color)]
        x += width
    total: float = sum(steps[key] for key, _ in TIME_STEPS)
    body += [text(x + 8, y + 15, f"{total:.0f} s, {sent_back(steps):.0f}% sent back", theme.ink, 12, 600)]
    return body


def sent_back(steps: dict[str, float]) -> float:
    return 100 * (1 - steps["merged_first_time"])


def time_bars(theme: Theme, merge: dict[str, dict[str, float]]) -> list[str]:
    arms: list[str] = [arm for arm in TIME_ARMS if arm in merge]
    top: float = max(sum(merge[arm][key] for key, _ in TIME_STEPS) for arm in arms)
    title: str = f"Agent time per task until merged (mean of {merge[arms[0]]['runs']:.0f} runs)"
    body: list[str] = [text(0, HISTORY_TOP - 22, title, theme.muted, 13, 600)]
    y: float = HISTORY_TOP
    for arm in arms:
        body += [text(0, y + 15, TIME_ARMS[arm], theme.ink, 13, 600)]
        body += time_row(theme, y, merge[arm], top)
        y += TIME_ROW_STEP
    for index, ((_, name), color) in enumerate(zip(TIME_STEPS, time_colors(theme), strict=True)):
        x: float = index * TIME_LEGEND_STEP
        body += [rect(x, y + 4, 12, 12, color), text(x + 18, y + 15, name, theme.muted, 11)]
    return body


def time_chart(theme: Theme, merge: dict[str, dict[str, float]], history: dict[str, Any]) -> str:
    """Where an agent's time goes until the reviewer merges, and the first answer's time by version."""
    seconds_top: float = 1.2 * max(max(entry["seconds"] for entry in history["versions"]), history["baseline"]["seconds"])
    panel: Panel = Panel(
        40.0 + HISTORY_PANEL_WIDTH + HISTORY_PANEL_GAP, "First answer by version (median)", "seconds", seconds_top, "s"
    )
    body: list[str] = [text(0, 26, "Time to a merged change", theme.ink, 18, 600)]
    body += time_bars(theme, merge) + history_panel(theme, panel, history)
    arms: str = "; ".join(
        f"{TIME_ARMS[arm]}: "
        + ", ".join(f"{name.lower()} {merge[arm][key]:.0f} s" for key, name in TIME_STEPS)
        + f", {sent_back(merge[arm]):.0f}% sent back"
        for arm in TIME_ARMS
        if arm in merge
    )
    versions: str = ", ".join(f"{entry['version']} {entry['seconds']:.0f} s" for entry in history["versions"])
    label: str = f"{arms}. First answer by version: {versions}; plain Claude {history['baseline']['seconds']:.0f} s."
    rows: int = sum(1 for arm in TIME_ARMS if arm in merge)
    legend_bottom: float = HISTORY_TOP + rows * TIME_ROW_STEP + 24
    return svg(int(max(HISTORY_TOP + HISTORY_PANEL_HEIGHT + 40, legend_bottom)), label, body)


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


STYLES: Path = Path(__file__).resolve().parent / "results" / "styles.json"
STYLE_ARMS: dict[str, str] = {
    "chef152": "Chef 1.5.2",
    "nolean": "Chef without lean.md",
    "caveman": "Caveman 4.1",
    "ponytail": "Ponytail 5.3",
}
STYLE_TASKS: tuple[str, ...] = ("python", "bugfix", "refactor", "docker", "github-actions", "sql", "typescript", "bash")
STYLE_ALL: str = "All contexts"
STYLE_CELL_HEIGHT: float = 26.0
STYLE_ROW_STEP: float = 32.0
STYLE_CELL_GAP: float = 8.0


@dataclass(frozen=True)
class StyleMetric:
    key: str
    title: str
    unit: str
    lower_is_better: bool


STYLE_METRICS: tuple[StyleMetric, ...] = (
    StyleMetric("accepted", "First answer accepted: points above or below plain Claude", "pt", False),
    StyleMetric("cost", "Cost per task, fixes included: % above or below plain Claude", "%", True),
    StyleMetric("lines", "Code to review: % above or below plain Claude", "%", True),
)


def style_value(loop: dict[str, float], key: str) -> float:
    return {
        "accepted": 100 * loop["merged_first_time"],
        "cost": loop["total_cost"] / loop["runs"],
        "lines": loop["lines_to_review"],
    }[key]


def style_gap(arm: dict[str, float], plain: dict[str, float], metric: StyleMetric) -> float:
    """Points for a rate, percent of plain Claude's value for an amount."""
    if metric.unit == "pt":
        return style_value(arm, metric.key) - style_value(plain, metric.key)
    return 100 * (style_value(arm, metric.key) / style_value(plain, metric.key) - 1)


def style_cell(theme: Theme, origin: tuple[float, float], width: float, gap: float, metric: StyleMetric) -> list[str]:
    better: bool = (gap < 0) if metric.lower_is_better else (gap > 0)
    fill: str = theme.track if round(gap) == 0 else theme.chef if better else theme.without
    x, y = origin
    shown: str = f"{gap:+.0f} {metric.unit}" if metric.unit == "pt" else f"{gap:+.0f}%"
    return [rect(x, y, width, STYLE_CELL_HEIGHT, fill), text(x + width / 2, y + 18, shown, theme.ink, 13, 600, "middle")]


def style_chart(theme: Theme, styles: dict[str, Any], metric: StyleMetric) -> str:
    """One row per context, one column per arm: each cell is the gap to plain Claude; the chef color marks a gain."""
    tasks: list[str] = [task for task in STYLE_TASKS if "none" in styles["tasks"].get(task, {})]
    arms: list[str] = [arm for arm in STYLE_ARMS if all(arm in styles["tasks"][task] for task in tasks)]
    gaps: dict[str, dict[str, float]] = {
        task: {arm: style_gap(styles["tasks"][task][arm], styles["tasks"][task]["none"], metric) for arm in arms}
        for task in tasks
    }
    gaps[STYLE_ALL] = {arm: statistics.fmean(gaps[task][arm] for task in tasks) for arm in arms}
    width: float = (WIDTH - LABEL_WIDTH) / len(arms) - STYLE_CELL_GAP
    body: list[str] = [text(0, 26, metric.title, theme.ink, 18, 600)]
    body += [
        text(LABEL_WIDTH + index * (width + STYLE_CELL_GAP) + width / 2, 62, STYLE_ARMS[arm], theme.muted, 13, 600, "middle")
        for index, arm in enumerate(arms)
    ]
    y: float = 76.0
    for row in [*tasks, STYLE_ALL]:
        body += [text(0, y + 18, TASK_NAMES.get(row, row), theme.ink, 14, 600)]
        for index, arm in enumerate(arms):
            body += style_cell(theme, (LABEL_WIDTH + index * (width + STYLE_CELL_GAP), y), width, gaps[row][arm], metric)
        y += STYLE_ROW_STEP
    label: str = f"{metric.title}, all contexts: " + ", ".join(f"{STYLE_ARMS[arm]} {gaps[STYLE_ALL][arm]:+.0f}" for arm in arms)
    return svg(int(y), label, body)


def main() -> None:
    summary: dict[str, Any] = json.loads(SUMMARY.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in (LIGHT, DARK):
        merge: dict[str, dict[str, float]] = json.loads(MERGE.read_text(encoding="utf-8"))["arms"]
        latest: dict[str, dict[str, float]] = (
            json.loads(MERGE_15.read_text(encoding="utf-8"))["arms"] if MERGE_15.is_file() else merge
        )
        (OUT / f"overview{theme.suffix}.svg").write_text(overview_chart(theme, merge), encoding="utf-8")
        if STACKS.is_file():
            stacks: dict[str, dict[str, float]] = json.loads(STACKS.read_text(encoding="utf-8"))["arms"]
            (OUT / f"stacks{theme.suffix}.svg").write_text(
                overview_chart(theme, stacks, STACKS_TITLE, STACKS_ARMS), encoding="utf-8"
            )
        (OUT / f"break-even{theme.suffix}.svg").write_text(break_even_chart(theme, latest), encoding="utf-8")
        (OUT / f"cost{theme.suffix}.svg").write_text(cost_chart(theme, summary), encoding="utf-8")
        (OUT / f"pairwise{theme.suffix}.svg").write_text(pairwise_chart(theme, summary), encoding="utf-8")
        (OUT / f"cost-split{theme.suffix}.svg").write_text(split_chart(theme), encoding="utf-8")
        if MERGE_15.is_file():
            release: dict[str, dict[str, float]] = json.loads(MERGE_15.read_text(encoding="utf-8"))["arms"]
            (OUT / f"overview-15{theme.suffix}.svg").write_text(
                overview_chart(theme, release, RELEASE_15_TITLE, RELEASE_15_ARMS), encoding="utf-8"
            )
        if QUALITY.is_file():
            quality: dict[str, Any] = json.loads(QUALITY.read_text(encoding="utf-8"))
            (OUT / f"quality{theme.suffix}.svg").write_text(quality_chart(theme, quality), encoding="utf-8")
        if HISTORY.is_file():
            history: dict[str, Any] = json.loads(HISTORY.read_text(encoding="utf-8"))
            for key in HISTORY_METRICS:
                (OUT / f"history-{key}{theme.suffix}.svg").write_text(history_chart(theme, history, key), encoding="utf-8")
            (OUT / f"time{theme.suffix}.svg").write_text(time_chart(theme, latest, history), encoding="utf-8")
        if STYLES.is_file():
            styles: dict[str, Any] = json.loads(STYLES.read_text(encoding="utf-8"))
            for metric in STYLE_METRICS:
                (OUT / f"styles-{metric.key}{theme.suffix}.svg").write_text(style_chart(theme, styles, metric), encoding="utf-8")


if __name__ == "__main__":
    main()
