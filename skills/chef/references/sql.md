# SQL, migrations

## Lint and format: SQLFluff

`.sqlfluff` at the repo root:

```ini
[sqlfluff]
dialect = postgres        # or tsql, mysql, sqlite, bigquery, snowflake...
templater = raw           # jinja or dbt if the project uses them
max_line_length = 100

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = upper

[sqlfluff:rules:capitalisation.identifiers]
extended_capitalisation_policy = lower
```

`sqlfluff lint` exits non-zero on any violation: that is the CI gate. Fix locally with `sqlfluff fix`. Lint migrations too.

## Schema changes: versioned migrations

- One migration tool per project: the framework's (EF Core, Alembic, Prisma, Ecto) or Flyway, Liquibase, Sqitch, Atlas.
- Migrations are numbered, committed and immutable once merged. Fix forward with a new migration.
- Every migration runs in a transaction where the database allows it, and has a tested rollback or a written reason why not.
- Never change the schema by hand in any shared environment.
- Split breaking changes (expand, migrate data, contract) so old and new code both run during a deploy.

## Code

- Parameterized queries only. Never build SQL by string concatenation or interpolation of input. Dynamic identifiers come from an allow-list.
- Explicit types (see SKILL.md): declare every column with a precise type and nullability. `NOT NULL` by default. `numeric(12, 2)` for money, `timestamptz` (or `datetimeoffset`) for time, never floats for money.
- Every table has a primary key. Foreign keys are declared, not implied. Add `CHECK` and `UNIQUE` constraints for business rules.
- Naming: `snake_case`, plural tables (`orders`), `id` primary key, `<table_singular>_id` foreign keys (`customer_id`). Name constraints and indexes: `pk_orders`, `fk_orders_customer_id`, `ix_orders_created_at`, `uq_users_email`.
- Index every foreign key and every column used in a frequent `WHERE`, `JOIN` or `ORDER BY`. Check plans with `EXPLAIN (ANALYZE)` before and after.
- List columns: no `SELECT *` in application code, no `INSERT` without a column list.
- Use explicit `JOIN ... ON`, never comma joins. CTEs over deep nested subqueries.
- In stored procedures and functions, declare parameter and return types; `SET NOCOUNT ON` and `THROW` in T-SQL.

## Tests

- Test against the real engine and version in a container (Testcontainers), never SQLite standing in for Postgres.
- Apply all migrations from empty in CI, then roll back and re-apply, to prove they run cleanly.
- Database logic (functions, procedures, triggers, constraints) gets unit tests in the database:
  - PostgreSQL: pgTAP, run with `pg_prove`.
  - SQL Server: tSQLt (`tSQLt.FakeTable` isolates dependencies).
- Repository and query code is covered by the application's integration tests, which count toward its 90% gate.
- No mainstream coverage or mutation tool exists for plain SQL; test each constraint and branch explicitly.

Order before done: `sqlfluff fix` then `sqlfluff lint` then migrations from empty then the database tests.
