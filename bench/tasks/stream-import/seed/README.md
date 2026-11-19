# ledger-import

Imports the CSV statements our banks export into the ledger database.

```
uv run ledger-import statement.csv --db ledger.sqlite3 --account ACME-EUR
```

Each row is validated. Invalid rows are reported with their line number and skipped; an import
stops as soon as more than `--max-errors` rows are invalid, and then nothing is written. Duplicate rows
(same date, amount and description) inside one file are reported and skipped.

The import goes through a `TransactionSink` (see `ledger_import/sinks.py`), so the same code
writes to SQLite in production and to memory in tests.

## Development

```
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```
