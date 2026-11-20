"""Validate the `[[endpoints]]` tables of a TOML config file."""

import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_SCHEMES = ("http", "https")
MAX_TIMEOUT_SECONDS = 300


def _url_problem(url: object) -> str | None:
    if not isinstance(url, str):
        return "url must be a string"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "url is not a valid URL"
    if parts.scheme not in ALLOWED_SCHEMES:
        return "url must use http or https"
    if not parts.hostname:
        return "url has no host"
    return None


def _timeout_problem(timeout: object) -> str | None:
    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        return "timeout must be a number"
    if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
        return f"timeout must be greater than 0 and at most {MAX_TIMEOUT_SECONDS}"
    return None


def _entry_problem(entry: object) -> str | None:
    if not isinstance(entry, dict):
        return "entry must be a table"
    if "url" not in entry:
        return "missing key: url"
    if "timeout" not in entry:
        return "missing key: timeout"
    return _url_problem(entry["url"]) or _timeout_problem(entry["timeout"])


def find_invalid(path: str) -> list[tuple[int, str]]:
    """Return the 0-based index and reason of each invalid endpoint, in file order.

    Raises OSError if the file cannot be read, ValueError (including
    tomllib.TOMLDecodeError and UnicodeDecodeError) if it is not valid TOML,
    or if `endpoints` is present but is not an array of tables.
    """
    text = Path(path).read_bytes().decode("utf-8")
    entries = tomllib.loads(text).get("endpoints", [])
    if not isinstance(entries, list):
        raise ValueError(f"{path}: 'endpoints' must be an array of tables")
    problems = ((index, _entry_problem(entry)) for index, entry in enumerate(entries))
    return [(index, problem) for index, problem in problems if problem is not None]


def main(argv: list[str]) -> int:
    """Print invalid endpoints; exit 0 if all valid, 1 if some invalid, 2 on usage/read error."""
    if len(argv) != 1:
        print("usage: python endpoints.py CONFIG.toml", file=sys.stderr)
        return 2
    try:
        invalid = find_invalid(argv[0])
    except (OSError, ValueError) as error:
        print(f"error: cannot read {argv[0]}: {error}", file=sys.stderr)
        return 2
    for index, reason in invalid:
        print(f"endpoints[{index}]: {reason}")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
