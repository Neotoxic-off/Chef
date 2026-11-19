import sqlite3
from pathlib import Path

import pytest

from ledger_import.cli import EXIT_ABORTED, EXIT_OK, EXIT_ROWS_REJECTED, EXIT_UNREADABLE_FILE, main

HEADER = "date,description,amount,currency\n"


def write_statement(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "statement.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def stored_rows(database: Path) -> list[tuple[str, str, str]]:
    connection = sqlite3.connect(database)
    try:
        return connection.execute(
            "SELECT booked_on, amount, description FROM ledger_transaction ORDER BY id"
        ).fetchall()
    finally:
        connection.close()


def test_imports_into_sqlite_and_prints_totals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    statement = write_statement(
        tmp_path, "2026-03-01,Coffee,-3.50,EUR\n2026-03-02,Salary,2500.00,EUR\n"
    )
    database = tmp_path / "ledger.sqlite3"
    assert main([str(statement), "--db", str(database), "--account", "ACME-EUR"]) == EXIT_OK
    assert stored_rows(database) == [
        ("2026-03-01", "-3.50", "Coffee"),
        ("2026-03-02", "2500.00", "Salary"),
    ]
    output = capsys.readouterr().out
    assert "imported 2 transactions, rejected 0 rows" in output
    assert "EUR +2496.50" in output


def test_reports_rejected_rows_with_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    statement = write_statement(tmp_path, "2026-03-01,Coffee,-3.50,EUR\nbad,Tea,1,EUR\n")
    database = tmp_path / "ledger.sqlite3"
    assert main([str(statement), "--db", str(database), "--account", "A"]) == EXIT_ROWS_REJECTED
    assert "line 3: invalid date 'bad'" in capsys.readouterr().err
    assert len(stored_rows(database)) == 1


def test_aborted_import_leaves_database_empty(tmp_path: Path) -> None:
    statement = write_statement(
        tmp_path, "2026-03-01,Coffee,-3.50,EUR\nbad,Tea,1,EUR\nbad,Tea,2,EUR\n"
    )
    database = tmp_path / "ledger.sqlite3"
    assert (
        main([str(statement), "--db", str(database), "--account", "A", "--max-errors", "1"])
        == EXIT_ABORTED
    )
    assert stored_rows(database) == []


def test_missing_file_is_reported(tmp_path: Path) -> None:
    database = tmp_path / "ledger.sqlite3"
    assert (
        main([str(tmp_path / "nope.csv"), "--db", str(database), "--account", "A"])
        == EXIT_UNREADABLE_FILE
    )


@pytest.mark.parametrize("value", ["-1", "many"])
def test_rejects_invalid_max_errors(tmp_path: Path, value: str) -> None:
    with pytest.raises(SystemExit) as exited:
        main(
            [
                str(tmp_path / "s.csv"),
                "--db",
                str(tmp_path / "db"),
                "--account",
                "A",
                "--max-errors",
                value,
            ]
        )
    assert exited.value.code == 2
