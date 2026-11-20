# Elasticsearch and OpenSearch

Written in November 2026 (not benchmarked): Elasticsearch 9.5.x, OpenSearch 3.10.x. Check https://github.com/elastic/elasticsearch/releases and https://github.com/opensearch-project/OpenSearch/releases.

## License and choice

- Elasticsearch source: AGPLv3, SSPL 1.0 or Elastic License 2.0 (AGPL option added in 2024, before 8.16). Default binary distributions stay under Elastic License 2.0. `x-pack` code is ELv2 only.
- OpenSearch: Apache 2.0, a Linux Foundation project.
- APIs have diverged since the fork. Use the client for the engine you run; do not mix.
- Search is a secondary index. The source of truth stays in the database; you must be able to rebuild the index from it.

## Mappings: explicit, not dynamic

- Set `"dynamic": "strict"` so unknown fields fail instead of creating mappings.
- `keyword` for IDs, enums, filters and sorting; `text` (with an analyzer) for full-text; both via `fields` only when you need both.
- Use `date`, `scaled_float` or `long` (cents) for money, `boolean`; never leave numbers as strings.
- `flattened` for open-ended key-value bags instead of exploding the mapping.
- Do not index secrets or personal data you do not search on (`"index": false`, or leave it out).

## Templates and aliases

Composable index templates (`_index_template`) own mappings and settings; legacy `_template` is deprecated.

```json
PUT _index_template/products
{
  "index_patterns": ["products-*"],
  "template": {
    "settings": { "number_of_shards": 1, "number_of_replicas": 1 },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "sku":   { "type": "keyword" },
        "name":  { "type": "text" },
        "price": { "type": "scaled_float", "scaling_factor": 100 },
        "updated_at": { "type": "date" }
      }
    }
  }
}
```

- The app reads and writes through aliases only (`products`, `products-write`), never concrete index names.
- Mapping change: create `products-v2`, `_reindex` from v1, then switch the alias atomically in one `_aliases` call. Keep v1 until v2 is verified: that is the rollback.
- Keep template and alias changes in versioned files applied by CI, like database migrations.

## Queries

- Put exact conditions (status, tenant, dates) in `bool.filter`: no scoring, cacheable. Only relevance clauses go in `must` or `should`.
- Never pass user input as `query_string` syntax; use `match`, `multi_match` or `simple_query_string`.
- Always filter by tenant in multi-tenant indexes, server side.
- Set `track_total_hits` to a bound or `false` when you do not need exact counts.

## Pagination

- `from` and `size` only for shallow pages; capped at 10 000 hits by `index.max_result_window`. Do not raise it.
- Deep paging: `search_after` with a point in time (PIT) and a sort with a tiebreaker. Elastic no longer recommends `scroll` for deep pagination.
- Keep `query` and `sort` identical across pages; send the newest PIT ID each time; close the PIT when done.

## Operations

- Shards: aim for a few tens of GB each; do not create one index per customer.
- Time-series data: data streams with lifecycle policies (ILM in Elasticsearch, ISM in OpenSearch).
- Security on: TLS, auth, roles per app. Snapshot to object storage and test restores.

## Tests

- Testcontainers Elasticsearch or OpenSearch module with the production version. Apply templates in setup, `refresh` before asserting.
- Test the reindex-and-swap script and a mapping rejection under `strict`.
