# MongoDB

Written in November 2026 (not benchmarked): server 9.0.x is current (tags on https://github.com/mongodb/mongo; release notes on https://www.mongodb.com/docs/manual/release-notes/). Prisma 7.0 shipped without MongoDB support (unverified for later 7.x: check the Prisma changelog); otherwise use the official driver.

## Schema design for access patterns

- List the queries first, then shape documents to answer each with one read.
- Embed what is read together and bounded (order lines in an order). Reference what grows without bound or is shared (customer from orders).
- Never let an array grow without limit: the 16 MB document limit and index cost will hit you. Use a child collection or the bucket pattern.
- Duplicate a few read-mostly fields (customer name on the order) when it saves a join; document who updates the copies.
- Version documents with a `schemaVersion` field and migrate lazily or with a scripted, reversible migration (`migrate-mongo` or the app's tool).

## Validation

Every collection has a `$jsonSchema` validator with `validationAction: "error"`.

```javascript
db.createCollection("orders", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["customerId", "status", "total", "createdAt"],
    additionalProperties: false,
    properties: {
      _id: { bsonType: "objectId" },
      customerId: { bsonType: "objectId" },
      status: { enum: ["open", "paid", "shipped"] },
      total: { bsonType: "decimal" },
      createdAt: { bsonType: "date" }
    }
  } },
  validationAction: "error"
});
```

- `decimal` (Decimal128) for money, `date` for time, never strings for either.
- Also validate in the app at the trust boundary; the validator is the last line, not the only one.

## Indexes

- Compound indexes follow ESR: Equality fields, then Sort, then Range.
- Check every hot query with `explain("executionStats")`: want `IXSCAN`, `totalDocsExamined` close to `nReturned`, no `SORT` stage in memory.
- Unique indexes for business keys; TTL indexes for expiring data; partial indexes for hot subsets.
- Build indexes in migrations, not on app start.

## Queries and safety

- Build filters from typed values, never from raw request JSON: a body like `{"$ne": null}` is operator injection. Reject keys starting with `$` and cast types first.
- Project only the fields you need.
- Paginate by range on an indexed field (`_id > lastId`), not big `skip`.

## Transactions

- Need a replica set or sharded cluster. Use them only for multi-document invariants; a single-document write is already atomic.
- Default limit: a transaction must run under one minute (`transactionLifetimeLimitSeconds`). Keep them small.
- Use the driver's `withTransaction` helper: it retries `TransientTransactionError` and `UnknownTransactionCommitResult` for you.
- Write concern `majority` for data you cannot lose.

## Aggregation pitfalls

- `$match` and `$project` first so indexes are used and less data flows.
- Each stage has a 100 MB memory limit; blocking stages (`$group`, `$sort`) spill to disk only when `allowDiskUse` is on (default from `allowDiskUseByDefault`). Spilling is slow: fix the pipeline first.
- `$lookup` per document on an unindexed `foreignField` is an N+1 inside the server. Index the foreign field or embed.
- `$push` in `$group` has its own 100 MB cap that errors even with `allowDiskUse`.

## Tests

- Testcontainers MongoDB module, started as a replica set so transactions work. Same major as production.
- Test validator rejections and the operator-injection guard.
