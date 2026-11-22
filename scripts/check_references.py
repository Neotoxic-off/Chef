"""Static checks over skills/chef/references: version line, links to other references, fenced blocks that parse,
and `docker run` lines: Git Bash path conversion off for `$PWD` mounts, every image listed in container-images.txt
(the weekly images workflow checks that each listed image still exists)."""

import ast
import json
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REFERENCES_DIR: Path = Path(__file__).resolve().parent.parent / "skills" / "chef" / "references"
INDEX_NAME: str = "INDEX.md"
# Line 3 names the versions: "Verified against ..." (benchmarked stacks), or "Written for ..., not benchmarked" or
# "Written in <Month> <year> (not benchmarked)" for the others.
VERSION_LINE: re.Pattern[str] = re.compile(
    r"\bVerified against\b|\bWritten for .+not benchmarked|\bWritten in [A-Z][a-z]+ \d{4} \(not benchmarked\)"
)
REFERENCE_MENTION: re.Pattern[str] = re.compile(r"\b([a-z0-9][a-z0-9-]*\.md)\b")
FENCE: re.Pattern[str] = re.compile(r"^\s*```(\S*)")
NOT_REFERENCES: frozenset[str] = frozenset({"SKILL.md", "README.md", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md", "TRANSFORM.md"})
IMAGES_FILE: Path = Path(__file__).resolve().parent / "container-images.txt"
# A tagged image name; `<tag>` placeholders, `$PWD:/w` mounts and port mappings (`8080:8080`) do not match.
IMAGE: re.Pattern[str] = re.compile(r"(?<![\w$/.:-])((?:[a-z0-9.-]+/)*[a-z0-9._-]*[a-z][a-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*)")
PWD_MOUNT: str = '-v "$PWD'
NO_PATH_CONVERSION: str = "MSYS_NO_PATHCONV=1"


class _AnyTagLoader(yaml.SafeLoader):
    """Safe loader that accepts custom tags (`!Ref`, `!reference`) as plain nodes."""


_AnyTagLoader.add_multi_constructor("", lambda loader, suffix, node: None)


def _parse_yaml(text: str) -> None:
    for _ in yaml.load_all(text, Loader=_AnyTagLoader):
        pass


def _parse_json(text: str) -> None:
    # An Elasticsearch console block starts with its request line (`PUT _index_template/x`).
    json.loads(re.sub(r"\A(GET|PUT|POST|DELETE|HEAD) \S+\n", "", text))


def _parse_python(text: str) -> None:
    # A notebook cell may use IPython magics (`%autoreload 2`) and shell escapes (`!pip ...`).
    ast.parse(re.sub(r"^\s*[%!]", "# ", text, flags=re.MULTILINE))


PARSERS: dict[str, Callable[[str], object]] = {
    "json": _parse_json,
    "yaml": _parse_yaml,
    "yml": _parse_yaml,
    "toml": tomllib.loads,
    "python": _parse_python,
    "py": _parse_python,
}


@dataclass
class Report:
    files: int = 0
    version_lines: int = 0
    links: int = 0
    parsed: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    images: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


def code_blocks(text: str) -> list[tuple[int, str, str]]:
    """Return (line number, language, body) for each fenced block; an unlabeled block has language ''."""
    blocks: list[tuple[int, str, str]] = []
    lines: list[str] = text.splitlines()
    index: int = 0
    while index < len(lines):
        match: re.Match[str] | None = FENCE.match(lines[index])
        if not match:
            index += 1
            continue
        start: int = index
        indent: int = len(lines[index]) - len(lines[index].lstrip())
        body: list[str] = []
        index += 1
        while index < len(lines) and not FENCE.match(lines[index]):
            body.append(lines[index][indent:])
            index += 1
        blocks.append((start + 1, match.group(1).lower(), "\n".join(body) + "\n"))
        index += 1
    return blocks


def check_docker_line(name: str, number: int, line: str, report: Report) -> None:
    if PWD_MOUNT in line and NO_PATH_CONVERSION not in line:
        report.errors.append(f"{name}:{number}: mounts $PWD without {NO_PATH_CONVERSION}, which Git Bash on Windows needs")
    report.images.update(IMAGE.findall(line))


def check_images(report: Report, listed: set[str]) -> None:
    for image in sorted(report.images - listed):
        report.errors.append(f"image {image} is run by a reference but not listed in {IMAGES_FILE.name}")
    for image in sorted(listed - report.images):
        report.errors.append(f"image {image} is listed in {IMAGES_FILE.name} but no reference runs it")


def read_images(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def check_file(path: Path, names: set[str], report: Report) -> None:
    text: str = path.read_text(encoding="utf-8")
    report.files += 1
    lines: list[str] = text.splitlines()
    if path.name != INDEX_NAME:
        report.version_lines += 1
        if len(lines) < 3 or not VERSION_LINE.search(lines[2]):
            report.errors.append(
                f"{path.name}:3: no version line ('Verified against ...', 'Written for ..., not benchmarked' or 'Written in <Month> <year> (not benchmarked)')"
            )
    for mention in REFERENCE_MENTION.findall(text):
        if mention in NOT_REFERENCES:
            continue
        report.links += 1
        if mention not in names:
            report.errors.append(f"{path.name}: mentions {mention}, which is not a reference")
    for number, source_line in enumerate(lines, start=1):
        if "docker run" in source_line:
            check_docker_line(path.name, number, source_line, report)
    for line, language, body in code_blocks(text):
        parser: Callable[[str], object] | None = PARSERS.get(language)
        if parser is None:
            report.skipped[language or "(none)"] += 1
            continue
        report.parsed[language] += 1
        try:
            parser(body)
        except (ValueError, SyntaxError, yaml.YAMLError) as error:
            first: str = str(error).splitlines()[0] if str(error) else type(error).__name__
            report.errors.append(f"{path.name}:{line}: {language} block does not parse: {first}")


def check_references(references_dir: Path) -> Report:
    paths: list[Path] = sorted(references_dir.glob("*.md"))
    names: set[str] = {path.name for path in paths}
    report: Report = Report()
    for path in paths:
        check_file(path, names, report)
    return report


def main() -> int:
    report: Report = check_references(REFERENCES_DIR)
    check_images(report, read_images(IMAGES_FILE))
    print(f"references: {report.version_lines} files have a version line on line 3")
    print(f"references: {len(report.images)} container images, all listed in {IMAGES_FILE.name}")
    print(f"references: {report.links} mentions of another reference in {report.files} files (with {INDEX_NAME}) resolve")
    print(f"references: {sum(report.parsed.values())} blocks parsed: {dict(sorted(report.parsed.items()))}")
    print(
        f"references: {sum(report.skipped.values())} blocks skipped (no offline parser): {dict(sorted(report.skipped.items()))}"
    )
    for error in report.errors:
        print(f"references: {error}", file=sys.stderr)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
