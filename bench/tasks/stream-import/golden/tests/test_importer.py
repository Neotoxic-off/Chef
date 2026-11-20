import csv
import io
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import pytest

from ledger_import import (
    ImportAbortedError,
    ImportFormatError,
    ImportOptions,
    ImportReport,
    InMemorySink,
    Transaction,
    import_csv,
    import_file,
)

HEADER = "date,description,amount,currency\n"
ACCOUNT = "ACME-EUR"


def run_import(
    text: str, options: ImportOptions | None = None
) -> tuple[InMemorySink, ImportReport]:
    sink = InMemorySink()
    report = import_csv(io.StringIO(text), sink, options or ImportOptions(account=ACCOUNT))
    return sink, report


class FailingSink(InMemorySink):
    def write_batch(self, transactions: Sequence[Transaction]) -> None:
        raise OSError("disk full")


def test_imports_valid_rows_and_sums_totals_per_currency() -> None:
    sink, report = run_import(
        HEADER
        + "2026-03-01,Coffee,-3.50,EUR\n"
        + "2026-03-02,Salary,2500.00,EUR\n"
        + "2026-03-02,Hotel,-120.00,USD\n"
    )
    assert report.imported == 3
    assert report.errors == []
    assert report.totals == {"EUR": Decimal("2496.50"), "USD": Decimal("-120.00")}
    assert [transaction.description for transaction in sink.committed] == [
        "Coffee",
        "Salary",
        "Hotel",
    ]
    assert {transaction.account for transaction in sink.committed} == {ACCOUNT}


def test_rejects_invalid_rows_with_their_line_number() -> None:
    sink, report = run_import(
        HEADER + "2026-03-01,Coffee,-3.50,EUR\nnot a date,Tea,-2.00,EUR\n2026-03-03,,-1.00,EUR\n"
    )
    assert report.imported == 1
    assert [str(error) for error in report.errors] == [
        "line 3: invalid date 'not a date'",
        "line 4: missing description",
    ]
    assert len(sink.committed) == 1


def test_line_numbers_count_multiline_quoted_fields() -> None:
    sink, report = run_import(
        HEADER + '2026-03-01,"Rent\nMarch",-900.00,EUR\n2026-03-02,Tea,oops,EUR\n'
    )
    assert sink.committed[0].description == "Rent March"
    assert [error.line for error in report.errors] == [4]


def test_rejects_duplicates_inside_one_file() -> None:
    _, report = run_import(HEADER + "2026-03-01,Coffee,-3.50,EUR\n2026-03-01,  coffee ,-3.50,EUR\n")
    assert report.imported == 1
    assert [str(error) for error in report.errors] == ["line 3: duplicate of an earlier row"]


def test_uses_default_currency_when_column_is_missing() -> None:
    sink, _ = run_import(
        "date,memo,amount\n2026-03-01,Coffee,-3.50\n",
        ImportOptions(account=ACCOUNT, default_currency="CHF"),
    )
    assert sink.committed[0].currency == "CHF"


def test_reads_debit_and_credit_columns() -> None:
    sink, _ = run_import(
        "Booking Date;Details;Debit;Credit\n01.03.2026;Coffee;3.50;\n02.03.2026;Refund;;10.00\n",
        ImportOptions(account=ACCOUNT, delimiter=";"),
    )
    assert [transaction.amount for transaction in sink.committed] == [
        Decimal("-3.50"),
        Decimal("10.00"),
    ]


def test_short_rows_are_rejected_not_crashing() -> None:
    _, report = run_import(HEADER + "2026-03-01,Coffee\n")
    assert [str(error) for error in report.errors] == ["line 2: missing amount"]


def test_aborts_and_writes_nothing_after_too_many_errors() -> None:
    sink = InMemorySink()
    text = HEADER + "2026-03-01,Coffee,-3.50,EUR\n" + "bad,row,x,EUR\n" * 3
    with pytest.raises(ImportAbortedError) as aborted:
        import_csv(io.StringIO(text), sink, ImportOptions(account=ACCOUNT, max_errors=2))
    assert len(aborted.value.report.errors) == 3
    assert sink.committed == []


def test_reaching_max_errors_exactly_does_not_abort() -> None:
    sink, report = run_import(
        HEADER + "2026-03-01,Coffee,-3.50,EUR\n" + "bad,row,x,EUR\n" * 2,
        ImportOptions(account=ACCOUNT, max_errors=2),
    )
    assert len(report.errors) == 2
    assert len(sink.committed) == 1


def test_sink_failure_rolls_back_and_propagates() -> None:
    sink = FailingSink()
    with pytest.raises(OSError, match="disk full"):
        import_csv(
            io.StringIO(HEADER + "2026-03-01,Coffee,-3.50,EUR\n"),
            sink,
            ImportOptions(account=ACCOUNT),
        )
    assert sink.committed == []


def test_header_only_file_imports_nothing() -> None:
    sink, report = run_import(HEADER)
    assert report.imported == 0
    assert sink.committed == []


@pytest.mark.parametrize("text", ["", "\n", "amount,currency\n1.00,EUR\n"])
def test_rejects_files_without_a_usable_header(text: str) -> None:
    with pytest.raises(ImportFormatError):
        run_import(text)


def test_import_file_strips_the_byte_order_mark(tmp_path: Path) -> None:
    path = tmp_path / "statement.csv"
    path.write_text("﻿" + HEADER + "2026-03-01,Coffee,-3.50,EUR\n", encoding="utf-8")
    report = import_file(path, InMemorySink(), ImportOptions(account=ACCOUNT))
    assert report.imported == 1


class RecordingSink(InMemorySink):
    def __init__(self) -> None:
        super().__init__()
        self.batch_sizes: list[int] = []

    def write_batch(self, transactions: Sequence[Transaction]) -> None:
        self.batch_sizes.append(len(transactions))
        super().write_batch(transactions)


def numbered_rows(count: int) -> str:
    return "".join(f"2026-03-01,Item {number},-1.00,EUR\n" for number in range(count))


def test_writes_full_batches_then_a_smaller_last_one() -> None:
    sink = RecordingSink()
    import_csv(
        io.StringIO(HEADER + numbered_rows(7)), sink, ImportOptions(account=ACCOUNT, batch_size=3)
    )
    assert sink.batch_sizes == [3, 3, 1]
    assert len(sink.committed) == 7


def test_never_writes_an_empty_batch() -> None:
    sink = RecordingSink()
    import_csv(
        io.StringIO(HEADER + numbered_rows(6)), sink, ImportOptions(account=ACCOUNT, batch_size=3)
    )
    assert sink.batch_sizes == [3, 3]
    empty = RecordingSink()
    import_csv(io.StringIO(HEADER), empty, ImportOptions(account=ACCOUNT))
    assert empty.batch_sizes == []


def test_first_batch_is_written_before_the_rest_is_read() -> None:
    class ExplodingStream(io.StringIO):
        def __init__(self, sink: RecordingSink) -> None:
            super().__init__(HEADER + numbered_rows(2))
            self.sink = sink
            self.written_before_end: bool | None = None

        def read(self, size: int | None = -1, /) -> str:
            text = super().read(size)
            if not text and self.written_before_end is None:
                self.written_before_end = bool(self.sink.batch_sizes)
            return text

    sink = RecordingSink()
    stream = ExplodingStream(sink)
    import_csv(stream, sink, ImportOptions(account=ACCOUNT, batch_size=1))
    assert stream.written_before_end is True


def test_failure_after_a_written_batch_leaves_the_sink_unchanged() -> None:
    sink = RecordingSink()
    text = HEADER + numbered_rows(2) + "bad,row,x,EUR\n" * 3
    with pytest.raises(ImportAbortedError):
        import_csv(
            io.StringIO(text), sink, ImportOptions(account=ACCOUNT, batch_size=1, max_errors=2)
        )
    assert sink.batch_sizes == [1, 1]
    assert sink.committed == []


def test_read_failure_midway_rolls_back_written_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenStream(io.StringIO):
        def read(self, size: int | None = -1, /) -> str:
            if self.tell() >= len(HEADER + numbered_rows(3)):
                raise UnicodeDecodeError("utf-8", b"x", 0, 1, "invalid start byte")
            return super().read(size)

    monkeypatch.setattr("ledger_import.importer.READ_CHUNK_SIZE", 40)
    sink = RecordingSink()
    stream = BrokenStream(HEADER + numbered_rows(3) + numbered_rows(3))
    with pytest.raises(UnicodeDecodeError):
        import_csv(stream, sink, ImportOptions(account=ACCOUNT, batch_size=1))
    assert sink.batch_sizes
    assert sink.committed == []


def test_interrupt_midway_rolls_back() -> None:
    class InterruptingSink(RecordingSink):
        def write_batch(self, transactions: Sequence[Transaction]) -> None:
            super().write_batch(transactions)
            if len(self.batch_sizes) == 2:
                raise KeyboardInterrupt

    sink = InterruptingSink()
    with pytest.raises(KeyboardInterrupt):
        import_csv(
            io.StringIO(HEADER + numbered_rows(5)),
            sink,
            ImportOptions(account=ACCOUNT, batch_size=1),
        )
    assert sink.committed == []


def test_batch_size_does_not_change_the_report() -> None:
    text = HEADER + numbered_rows(5) + "bad,row,x,EUR\n2026-03-01,Item 1,-1.00,EUR\n"
    _, small = run_import(text, ImportOptions(account=ACCOUNT, batch_size=2))
    _, large = run_import(text)
    assert small == large
    assert [str(error) for error in small.errors] == [
        "line 7: invalid amount 'x'",
        "line 8: duplicate of an earlier row",
    ]


def test_reads_identically_when_lines_span_read_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ledger_import.importer.READ_CHUNK_SIZE", 4)
    sink, report = run_import(
        "﻿" + HEADER + '2026-03-01,"Rent\r\nMarch",-9.00,EUR\r\nbad,x,1,EUR\r\n'
    )
    assert sink.committed[0].description == "Rent March"
    assert [error.line for error in report.errors] == [4]


def test_a_lone_carriage_return_still_fails_the_import_and_rolls_back() -> None:
    sink = RecordingSink()
    text = HEADER + "2026-03-01,Coffee,-3.50,EUR\r2026-03-02,Tea,-2.00,EUR\n"
    with pytest.raises(csv.Error):
        import_csv(io.StringIO(text), sink, ImportOptions(account=ACCOUNT))
    assert sink.committed == []


def test_last_line_without_newline_is_imported() -> None:
    sink, _ = run_import(HEADER + "2026-03-01,Coffee,-3.50,EUR")
    assert len(sink.committed) == 1


@pytest.mark.parametrize(
    "options",
    [
        {"account": ACCOUNT, "batch_size": 0},
        {"account": ACCOUNT, "batch_size": -5},
        {"account": ACCOUNT, "max_errors": -1},
        {"account": ACCOUNT, "delimiter": ""},
        {"account": ACCOUNT, "delimiter": ";;"},
        {"account": " "},
    ],
)
def test_options_are_validated(options: dict[str, str | int]) -> None:
    with pytest.raises(ValueError):
        ImportOptions(**options)  # type: ignore[arg-type]
