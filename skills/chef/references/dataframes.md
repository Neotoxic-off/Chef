# DataFrames: pandas, Polars, pandera

Builds on `python.md`. Verified November 2026 on PyPI: pandas 3.1, Polars 2.1, pandera 0.36, pandas-stubs 3.1. Check current versions with `uv tree --outdated` or `https://pypi.org/project/<name>/`.

## Pick the library

- New code: Polars, lazy API (`scan_*`, then `collect()`). pandas when a dependency needs it or the code base already uses it. Never iterate rows (`iterrows`, `for` over rows, `apply` with a Python lambda). Use column expressions.
- Parquet between steps; CSV only at the edge, read with an explicit schema.

## Types and schemas

- Declare dtypes on read. No inference on production paths.
- Validate every DataFrame that crosses a boundary (file, database, API, another team) with a pandera `DataFrameModel`; annotate functions with the typed frame.
- `strict = True` so unexpected columns fail. `coerce = True` only at ingestion, never in the middle of a pipeline.
- `validate(frame, lazy=True)` in batch jobs to report every failure at once.

```python
import pandera.polars as pa
import polars as pl
from pandera.typing.polars import DataFrame

MIN_QUANTITY: int = 1


class Orders(pa.DataFrameModel):
    order_id: int = pa.Field(unique=True)
    customer_id: int
    sku: str
    quantity: int = pa.Field(ge=MIN_QUANTITY)

    class Config:
        strict = True


class CustomerQuantities(pa.DataFrameModel):
    customer_id: int = pa.Field(unique=True)
    total_quantity: int


@pa.check_types
def quantity_by_customer(orders: DataFrame[Orders]) -> DataFrame[CustomerQuantities]:
    totals: pl.DataFrame = (
        orders.group_by("customer_id").agg(pl.col("quantity").sum().alias("total_quantity"))
    )
    return CustomerQuantities.validate(totals.sort("customer_id"))
```

- Read with an explicit `pl.Schema` (`pl.scan_csv(path, schema=ORDERS_SCHEMA)`), then `Orders.validate(lazy_frame)`. On a `LazyFrame`, pandera checks names and dtypes without collecting; value checks collect.

## Polars 2

- `collect()` now defaults to the streaming engine, which does not guarantee row order. Sort explicitly, or pass `maintain_order` where the operation has it.
- Some 2.0 changes are silent (selector `&` with `pl.col`, `pl.datetime` output names). Read `https://docs.pola.rs/releases/upgrade/2/` before upgrading and diff outputs, not only exit codes.
- `pl.Enum` for known categories, `pl.Decimal` for money, timezone-aware `pl.Datetime`.

## pandas 3

- Copy-on-Write is the only mode: no chained assignment (`df["a"][mask] = x`); use `df.loc[mask, "a"] = x`.
- Text columns default to the `str` dtype, not `object`. Do not test for `object` to find strings.
- Add `pandas-stubs` so mypy checks pandas calls. Use `pd.ArrowDtype` or nullable dtypes (`"Int64"`, `"boolean"`) instead of float columns for missing integers.

## Data hygiene

- Never print or log `head()`, samples or failure cases of frames holding personal data; log counts and column names.
- Pin the input data version (file hash, table snapshot, Delta/Iceberg version) next to the result.

## Tests

- `polars.testing.assert_frame_equal` / `pandas.testing.assert_frame_equal` on small hand-built frames, one per behavior.
- Test schemas too: one valid frame passes, each rule has a frame that fails with `pa.errors.SchemaError`.
