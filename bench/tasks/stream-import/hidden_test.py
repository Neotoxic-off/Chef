"""Hidden test of the stream-import task: batching, streaming, all-or-nothing writes, and the behaviour that must not change."""

import io
import sqlite3
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import pytest
from ledger_import import (
    ImportAbortedError,
    ImportOptions,
    ImportReport,
    InMemorySink,
    SqliteSink,
    Transaction,
    import_csv,
    import_file,
)
from ledger_import.cli import EXIT_ABORTED, EXIT_OK, main

HEADER: str = "date,description,amount,currency\n"
ACCOUNT: str = "ACME-EUR"
# About 4.2 MB: reading in blocks of up to 2 MiB still counts as streaming, reading it all at once does not.
LARGE_ROW_COUNT: int = 120_000


def rows(count: int) -> str:
    return "".join(f"2026-03-01,Payment {index},-1.00,EUR\n" for index in range(count))


class SpySink(InMemorySink):
    """Records every call, and how far the input stream was read when each batch arrived."""

    def __init__(self, stream: io.StringIO | None = None, fail_on_write: int | None = None) -> None:
        super().__init__()
        self.calls: list[str] = []
        self.batch_sizes: list[int] = []
        self.positions: list[int] = []
        self._stream: io.StringIO | None = stream
        self._fail_on_write: int | None = fail_on_write

    def begin(self) -> None:
        self.calls.append("begin")
        super().begin()

    def write_batch(self, transactions: Sequence[Transaction]) -> None:
        self.calls.append("write")
        self.batch_sizes.append(len(transactions))
        if self._stream is not None:
            self.positions.append(self._stream.tell())
        if self._fail_on_write == len(self.batch_sizes):
            raise OSError("disk full")
        super().write_batch(transactions)

    def commit(self) -> None:
        self.calls.append("commit")
        super().commit()

    def rollback(self) -> None:
        self.calls.append("rollback")
        super().rollback()


class FailingStream(io.StringIO):
    """A file whose disk fails at a given offset, whether it is read by lines or by blocks."""

    def __init__(self, text: str, readable_chars: int) -> None:
        super().__init__(text)
        self._readable_chars: int = readable_chars

    def _check_offset(self) -> None:
        if self.tell() >= self._readable_chars:
            raise OSError("read error")

    def readline(self, size: int | None = -1) -> str:
        self._check_offset()
        return super().readline(size)

    def __next__(self) -> str:
        self._check_offset()
        return super().__next__()

    def read(self, size: int | None = -1) -> str:
        if size is None or size < 0:
            raise OSError("read error")
        self._check_offset()
        return super().read(min(size, self._readable_chars - self.tell()))


def import_text(text: str, sink: InMemorySink, **options: int) -> ImportReport:
    return import_csv(io.StringIO(text), sink, ImportOptions(account=ACCOUNT, **options))


def test_default_batch_size_is_500() -> None:
    assert ImportOptions(account=ACCOUNT).batch_size == 500


def test_writes_full_batches_then_the_rest_in_one_transaction() -> None:
    sink = SpySink()
    report = import_text(HEADER + rows(5), sink, batch_size=2)
    assert sink.batch_sizes == [2, 2, 1]
    assert sink.calls == ["begin", "write", "write", "write", "commit"]
    assert report.imported == 5
    assert [transaction.description for transaction in sink.committed] == [f"Payment {index}" for index in range(5)]


def test_default_batches_hold_500_rows() -> None:
    sink = SpySink()
    import_text(HEADER + rows(1001), sink)
    assert sink.batch_sizes == [500, 500, 1]


def test_never_writes_an_empty_batch() -> None:
    sink = SpySink()
    import_text(HEADER + rows(4), sink, batch_size=2)
    assert sink.batch_sizes == [2, 2]


def test_header_only_file_writes_no_batch() -> None:
    sink = SpySink()
    report = import_text(HEADER, sink, batch_size=2)
    assert sink.batch_sizes == []
    assert report.imported == 0
    assert "rollback" not in sink.calls


def test_rejected_rows_do_not_count_towards_a_batch() -> None:
    sink = SpySink()
    import_text(
        HEADER + "2026-03-01,A,-1.00,EUR\nbad,B,-1.00,EUR\n2026-03-01,C,-1.00,EUR\n2026-03-01,D,-1.00,EUR\n", sink, batch_size=2
    )
    assert sink.batch_sizes == [2, 1]


def test_batches_are_written_while_the_file_is_still_being_read() -> None:
    text = HEADER + rows(LARGE_ROW_COUNT)
    stream = io.StringIO(text)
    sink = SpySink(stream)
    import_csv(stream, sink, ImportOptions(account=ACCOUNT, batch_size=1000))
    assert len(sink.batch_sizes) == LARGE_ROW_COUNT // 1000
    assert sink.positions[0] < len(text) // 2


def test_duplicate_of_a_row_from_an_earlier_batch_is_rejected() -> None:
    sink = SpySink()
    text = HEADER + rows(3) + "2026-03-01,payment 0,-1.00,EUR\n"
    report = import_text(text, sink, batch_size=2)
    assert [str(error) for error in report.errors] == ["line 5: duplicate of an earlier row"]
    assert sink.batch_sizes == [2, 1]


MIXED_STATEMENT: str = (
    HEADER
    + "2026-03-01,Coffee,-3.50,EUR\n"
    + "2026-03-02,Salary,2500.00,EUR\n"
    + "not a date,Tea,-2.00,EUR\n"
    + '2026-03-02,"Hotel\nParis",-120.00,USD\n'
    + "2026-03-01,  coffee ,-3.50,EUR\n"
    + "2026-03-03,Train,(45.10),eur\n"
    + "2026-03-04,Refund,12.00,XXXX\n"
    + "2026-03-05,Book,-15.00,\n"
)


@pytest.mark.parametrize("batch_size", [1, 2, 3, 500])
def test_report_does_not_depend_on_the_batch_size(batch_size: int) -> None:
    sink = SpySink()
    report = import_text(MIXED_STATEMENT, sink, batch_size=batch_size)
    assert report.imported == 5
    assert report.totals == {"EUR": Decimal("2436.40"), "USD": Decimal("-120.00")}
    assert [str(error) for error in report.errors] == [
        "line 4: invalid date 'not a date'",
        "line 7: duplicate of an earlier row",
        "line 9: invalid currency 'XXXX'",
    ]
    assert [transaction.description for transaction in sink.committed] == ["Coffee", "Salary", "Hotel Paris", "Train", "Book"]


def test_byte_order_mark_is_still_ignored_on_streams() -> None:
    sink = SpySink()
    report = import_text("﻿" + HEADER + rows(3), sink, batch_size=2)
    assert report.imported == 3


def test_abort_after_batches_were_written_leaves_the_sink_unchanged() -> None:
    sink = SpySink()
    text = HEADER + rows(6) + "bad,X,-1.00,EUR\nbad,Y,-1.00,EUR\n"
    with pytest.raises(ImportAbortedError) as aborted:
        import_text(text, sink, batch_size=2, max_errors=1)
    assert len(aborted.value.report.errors) == 2
    assert sink.batch_sizes[:3] == [2, 2, 2]
    assert sink.committed == []
    assert "rollback" in sink.calls
    assert "commit" not in sink.calls


def test_read_failure_midway_leaves_the_sink_unchanged() -> None:
    text = HEADER + rows(LARGE_ROW_COUNT)
    stream = FailingStream(text, readable_chars=len(text) // 2)
    sink = SpySink()
    with pytest.raises(OSError, match="read error"):
        import_csv(stream, sink, ImportOptions(account=ACCOUNT, batch_size=1000))
    assert sink.batch_sizes != []
    assert sink.committed == []
    assert "commit" not in sink.calls


def test_sink_failure_on_a_later_batch_leaves_the_sink_unchanged() -> None:
    sink = SpySink(fail_on_write=2)
    with pytest.raises(OSError, match="disk full"):
        import_text(HEADER + rows(5), sink, batch_size=2)
    assert sink.committed == []
    assert "rollback" in sink.calls
    assert "commit" not in sink.calls


@pytest.mark.parametrize("batch_size", [0, -1])
def test_rejects_a_batch_size_below_one(batch_size: int) -> None:
    with pytest.raises(ValueError):
        import_text(HEADER + rows(1), InMemorySink(), batch_size=batch_size)


def test_import_file_writes_in_batches(tmp_path: Path) -> None:
    path = tmp_path / "statement.csv"
    path.write_text("﻿" + HEADER + rows(1200), encoding="utf-8")
    sink = SpySink()
    report = import_file(path, sink, ImportOptions(account=ACCOUNT))
    assert report.imported == 1200
    assert sink.batch_sizes == [500, 500, 200]


def stored_count(database: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        row: tuple[int] = connection.execute("SELECT COUNT(*) FROM ledger_transaction").fetchone()
    finally:
        connection.close()
    return row[0]


def test_cli_batch_size_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sizes: list[int] = []
    original = SqliteSink.write_batch

    def recording_write_batch(self: SqliteSink, transactions: Sequence[Transaction]) -> None:
        sizes.append(len(transactions))
        original(self, transactions)

    monkeypatch.setattr(SqliteSink, "write_batch", recording_write_batch)
    statement = tmp_path / "statement.csv"
    statement.write_text(HEADER + rows(5), encoding="utf-8")
    database = tmp_path / "ledger.sqlite3"
    assert main([str(statement), "--db", str(database), "--account", ACCOUNT, "--batch-size", "2"]) == EXIT_OK
    assert sizes == [2, 2, 1]
    assert stored_count(database) == 5


def test_cli_aborted_import_after_written_batches_leaves_database_empty(tmp_path: Path) -> None:
    statement = tmp_path / "statement.csv"
    statement.write_text(HEADER + rows(5) + "bad,X,-1.00,EUR\n", encoding="utf-8")
    database = tmp_path / "ledger.sqlite3"
    arguments = [str(statement), "--db", str(database), "--account", ACCOUNT, "--batch-size", "1", "--max-errors", "0"]
    assert main(arguments) == EXIT_ABORTED
    assert stored_count(database) == 0


@pytest.mark.parametrize("value", ["0", "-3", "many"])
def test_cli_rejects_an_invalid_batch_size(tmp_path: Path, value: str) -> None:
    statement = tmp_path / "statement.csv"
    statement.write_text(HEADER + rows(1), encoding="utf-8")
    with pytest.raises(SystemExit) as exited:
        main([str(statement), "--db", str(tmp_path / "ledger.sqlite3"), "--account", ACCOUNT, "--batch-size", value])
    assert exited.value.code == 2
