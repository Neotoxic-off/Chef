from pathlib import Path

import pytest

from endpoints import find_invalid, main


def write_config(tmp_path: Path, body: str) -> str:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return str(path)


def entry(url: str, timeout: str) -> str:
    return f'[[endpoints]]\nurl = "{url}"\ntimeout = {timeout}\n'


def test_valid_entries_return_empty_list(tmp_path: Path) -> None:
    body = entry("http://a.com", "5") + entry("https://b.com:8080/x", "0.5")
    assert find_invalid(write_config(tmp_path, body)) == []


def test_no_endpoints_returns_empty_list(tmp_path: Path) -> None:
    assert find_invalid(write_config(tmp_path, "title = 'x'\n")) == []


@pytest.mark.parametrize("timeout", ["300", "300.0", "0.001"])
def test_timeout_bounds_accepted(tmp_path: Path, timeout: str) -> None:
    assert find_invalid(write_config(tmp_path, entry("http://a.com", timeout))) == []


@pytest.mark.parametrize(
    ("timeout", "reason"),
    [
        ("0", "timeout must be greater than 0 and at most 300"),
        ("-1", "timeout must be greater than 0 and at most 300"),
        ("300.1", "timeout must be greater than 0 and at most 300"),
        ("nan", "timeout must be greater than 0 and at most 300"),
        ("inf", "timeout must be greater than 0 and at most 300"),
        ("true", "timeout must be a number"),
        ('"5"', "timeout must be a number"),
        ("[1]", "timeout must be a number"),
    ],
)
def test_bad_timeout_is_reported(tmp_path: Path, timeout: str, reason: str) -> None:
    assert find_invalid(write_config(tmp_path, entry("http://a.com", timeout))) == [(0, reason)]


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("ftp://a.com", "url must use http or https"),
        ("a.com", "url must use http or https"),
        ("", "url must use http or https"),
        ("http://", "url has no host"),
        ("https:///path", "url has no host"),
        ("http://[::1", "url is not a valid URL"),
    ],
)
def test_bad_url_is_reported(tmp_path: Path, url: str, reason: str) -> None:
    assert find_invalid(write_config(tmp_path, entry(url, "5"))) == [(0, reason)]


def test_non_string_url_is_reported(tmp_path: Path) -> None:
    body = "[[endpoints]]\nurl = 5\ntimeout = 5\n"
    assert find_invalid(write_config(tmp_path, body)) == [(0, "url must be a string")]


def test_missing_keys_are_reported(tmp_path: Path) -> None:
    body = '[[endpoints]]\ntimeout = 5\n[[endpoints]]\nurl = "http://a.com"\n[[endpoints]]\n'
    assert find_invalid(write_config(tmp_path, body)) == [
        (0, "missing key: url"),
        (1, "missing key: timeout"),
        (2, "missing key: url"),
    ]


def test_indexes_follow_file_order(tmp_path: Path) -> None:
    body = entry("http://a.com", "5") + entry("gopher://x", "5") + entry("http://b.com", "0")
    result = find_invalid(write_config(tmp_path, body))
    assert [index for index, _ in result] == [1, 2]


def test_non_table_entry_is_reported(tmp_path: Path) -> None:
    assert find_invalid(write_config(tmp_path, "endpoints = [1]\n")) == [
        (0, "entry must be a table")
    ]


def test_endpoints_not_a_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be an array of tables"):
        find_invalid(write_config(tmp_path, "endpoints = 'x'\n"))


def test_invalid_toml_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Expected"):
        find_invalid(write_config(tmp_path, "[[endpoints\n"))


def test_non_utf8_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        find_invalid(str(path))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_invalid(str(tmp_path / "nope.toml"))


def test_main_prints_invalid_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path, entry("ftp://a", "5"))
    assert main([path]) == 1
    assert capsys.readouterr().out == "endpoints[0]: url must use http or https\n"


def test_main_valid_exits_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write_config(tmp_path, entry("http://a.com", "5"))]) == 0
    assert capsys.readouterr().out == ""


def test_main_unreadable_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = str(tmp_path / "nope.toml")
    assert main([missing]) == 2
    assert f"error: cannot read {missing}" in capsys.readouterr().err


def test_main_wrong_arguments_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err
