from pathlib import Path

from endpoints import find_invalid

CONFIG = """
[[endpoints]]
url = "https://api.example.com"
timeout = 5

[[endpoints]]
url = "ftp://files.example.com"
timeout = 5

[[endpoints]]
url = "https://api.example.com"
timeout = 0

[[endpoints]]
timeout = 5

[[endpoints]]
url = "http://api.example.com"
timeout = 301

[[endpoints]]
url = "http://api.example.com:8080/v1"
timeout = 2.5

[[endpoints]]
url = "https://api.example.com"
timeout = "5"

[[endpoints]]
url = "https://"
timeout = 5

[[endpoints]]
url = "https://api.example.com"
timeout = true
"""


def test_find_invalid_returns_indexes_of_invalid_entries(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "endpoints.toml"
    config_path.write_text(CONFIG, encoding="utf-8")

    invalid: list[tuple[int, str]] = find_invalid(str(config_path))

    assert [index for index, _ in invalid] == [1, 2, 3, 4, 6, 7, 8]
