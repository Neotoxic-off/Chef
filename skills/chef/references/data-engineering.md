# Data engineering: Airflow, Dagster, dbt, Spark

Builds on `python.md`, `sql.md` and `dataframes.md`. Written in November 2026 (not benchmarked) on PyPI: Airflow 3.4, Dagster 1.13, dbt-core 1.12, PySpark 4.3. Check current versions on `https://pypi.org/project/<name>/`.

## Idempotent jobs

- Each run processes one explicit interval or partition and replaces exactly that slice: `MERGE`, `INSERT OVERWRITE`, or delete-and-insert in one transaction. Never append blindly.
- Rerunning or backfilling a slice gives the same result. No `now()` in job logic: use the run's logical interval.
- Write atomically: to a staging table or a transactional format (Delta, Iceberg), then commit or swap. Inputs are read by version or snapshot when the source allows it, and that version is logged.

## Airflow 3

- Author with the Task SDK: `from airflow.sdk import dag, task, Asset`. DAG files do no I/O at import; the scheduler parses them often.
- Tasks are thin: read `data_interval_start` / `data_interval_end` from the context and call a tested function in your package.
- Set `catchup`, `max_active_runs`, `retries` and `retry_delay` explicitly. Credentials come from Connections or a secrets backend; never put them in code, Variables or Asset URIs.
- Test: every DAG file imports without errors; run a DAG locally with `dag.test()`.

## Dagster

- Model data as assets with partitions; checks as `@asset_check`, blocking downstream when they fail. External systems are `ConfigurableResource`s injected into assets; tests pass fakes and call `materialize()`.

## dbt

- Public and mart models enforce contracts; incremental models declare `unique_key` and fail on schema drift.

```yaml
models:
  - name: fct_orders
    config:
      materialized: incremental
      incremental_strategy: merge
      unique_key: order_id
      on_schema_change: fail
      contract:
        enforced: true
    columns:
      - name: order_id
        data_type: bigint
        constraints:
          - type: not_null
        data_tests:
          - unique
      - name: amount
        data_type: numeric(12, 2)
        constraints:
          - type: not_null
```

- Data tests (`unique`, `not_null`, `relationships`, `accepted_values`) on every key and business rule; `dbt source freshness` on sources.
- Unit tests (YAML `unit_tests:`) for non-trivial SQL logic; run them in CI, exclude them from production builds with `--exclude-resource-type unit_test`.
- CI builds changed models and their children against production state: `dbt build --select state:modified+ --defer --state <prod-artifacts>`.
- Lint with SQLFluff using the `dbt` templater (see `sql.md`).

## Spark

- Read with an explicit schema and `FAILFAST`; never `inferSchema` in production.

```python
ORDERS_SCHEMA: StructType = StructType([
    StructField("order_id", LongType(), nullable=False),
    StructField("amount", DecimalType(MONEY_PRECISION, MONEY_SCALE), nullable=False),
    StructField("order_date", DateType(), nullable=False),
])
orders: DataFrame = spark.read.schema(ORDERS_SCHEMA).option("mode", "FAILFAST").json(source_path)
```

- Overwrite only touched partitions: `spark.sql.sources.partitionOverwriteMode=dynamic`, or `MERGE` on Delta/Iceberg.
- Built-in functions over Python UDFs; Pandas/Arrow UDFs when a UDF is unavoidable. Test transformations with a local `SparkSession` fixture and `pyspark.testing.assertDataFrameEqual`.

## Data contracts and data tests

- The producer owns the schema of each shared dataset, versioned in the repo; breaking changes go through expand, migrate, contract (see `sql.md`).
- Check at every boundary: schema, freshness, volume, uniqueness, nulls, referential integrity. A failed check stops downstream work; it is not only an alert.
- Never log row samples with personal data; mask or drop personal columns as early as possible.
