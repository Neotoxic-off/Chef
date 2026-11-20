# PostgreSQL

Builds on `sql.md` (lint, naming, parameterized queries, Testcontainers). Written in November 2026 (not benchmarked) against PostgreSQL 18.x (current major; check https://www.postgresql.org/versions.json) and PgBouncer 1.26.x (check https://www.pgbouncer.org/changelog.html).

## Schema

- `bigint generated always as identity` or `uuid` keys. PG 18 has `uuidv7()` (time-ordered, index-friendly); use it over `gen_random_uuid()` for new keys.
- `text` with a `CHECK (char_length(x) <= n)` over `varchar(n)` when the limit is a business rule. `jsonb`, never `json`, and only for truly schemaless parts.
- PG 18 generated columns are virtual by default; write `STORED` when you need to index the value.
- Enforce rules in the database: `NOT NULL`, `CHECK`, `UNIQUE`, foreign keys, exclusion constraints for overlaps (`EXCLUDE USING gist`).

## Indexes and plans

- B-tree by default; GIN for `jsonb`, arrays and full-text; BRIN for huge append-only time columns.
- Composite index column order: equality columns first, then range or sort columns.
- Partial indexes for hot subsets: `CREATE INDEX ix_orders_open ON orders (created_at) WHERE status = 'open';`.
- Read plans with `EXPLAIN (ANALYZE, BUFFERS)`. Look for `Seq Scan` on big tables, row estimates far from actuals, and `Sort` spilling to disk. `ANALYZE` stale tables before judging.
- Turn on `pg_stat_statements` and fix the top queries by total time, not by guess.
- Drop unused indexes (`pg_stat_user_indexes.idx_scan = 0` over a full business cycle): each one slows writes.

## Transactions and isolation

- Default is `READ COMMITTED`. Use `REPEATABLE READ` or `SERIALIZABLE` only on purpose, and retry the whole transaction on SQLSTATE `40001` and `40P01`.
- Keep transactions short: no network calls or user waits inside them.
- Job queues in a table: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n`.
- Set `statement_timeout` and `idle_in_transaction_session_timeout` per role so a stuck client cannot hold locks forever.

## Connection pooling: PgBouncer

- One pool in front of the database; size app pools so the total stays under `max_connections`.
- `pool_mode = transaction` for web apps. It breaks session state: no session `SET`, `LISTEN`, session advisory locks or temp tables across transactions. Use `SET LOCAL` inside the transaction.
- Protocol-level prepared statements work in transaction mode through `max_prepared_statements` (docs default: 200). SQL-level `PREPARE`/`EXECUTE` are not tracked.
- Keep PgBouncer patched: 1.26.1 fixed two CVEs (auth impersonation, CPU spin).

## Migrations, zero downtime

Use the project's tool (see `sql.md`). Lint migrations with `squawk` where it fits. Every migration has a down step or a written reason.

```sql
-- migration 1
SET LOCAL lock_timeout = '5s';
ALTER TABLE orders ADD COLUMN customer_ref bigint;
ALTER TABLE orders ADD CONSTRAINT fk_orders_customer_ref
    FOREIGN KEY (customer_ref) REFERENCES customers (id) NOT VALID;

-- migration 2, a separate transaction
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_customer_ref;
```

- `CREATE INDEX CONCURRENTLY` (and `DROP INDEX CONCURRENTLY`) for live tables; it cannot run inside a transaction block, so put it in its own non-transactional migration.
- Add `CHECK` and foreign keys `NOT VALID`, then `VALIDATE` in a later step. PG 18 also allows `NOT NULL ... NOT VALID`.
- Backfill in batches of a few thousand rows per transaction, never one giant `UPDATE`.
- Rename or retype a column with expand and contract: add new, dual-write, backfill, switch reads, drop old in a later release.

## Backups

- Physical backups plus WAL archiving for point-in-time recovery: pgBackRest or Barman (or the managed service's PITR). `pg_dump` is for logical copies, not your only backup.
- Encrypt backups and keep one copy off the primary account or region.
- Test restores on a schedule and time them. An untested backup is not a backup.

## Tests

- Testcontainers `postgres:<same major as prod>` image. Run migrations from empty, then the integration tests.
- Test the `40001` retry path and the constraint violations, not only the happy path.
