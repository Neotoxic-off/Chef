# Messaging: Kafka and RabbitMQ

Written in November 2026 (not benchmarked): Apache Kafka 4.4.x, RabbitMQ 4.4.x. Check https://kafka.apache.org/downloads and https://github.com/rabbitmq/rabbitmq-server/releases.

## Pick the tool

- Kafka: ordered, replayable event log, high throughput, many independent consumers. KRaft only since 4.0 (no ZooKeeper).
- RabbitMQ: work queues, routing, per-message acknowledgement. Replicated queues are quorum queues or streams; classic mirrored queues were removed in 4.0.
- Kafka share groups (queue semantics on a topic, per-record ack, delivery counts) are production-ready since 4.2. Use them only when records are processed one at a time, not as an ordered stream.

## Delivery: at-least-once, idempotent consumers

- Assume every message can arrive twice and out of order across keys. Exactly-once end to end does not exist across your database and the broker.
- Commit the offset or `ack` only after the side effect is durable. Never auto-ack before processing.
- Every message carries a unique `messageId`. The consumer records processed IDs in the same transaction as its side effect.

```sql
INSERT INTO processed_messages (message_id, processed_at)
VALUES ($1, now())
ON CONFLICT (message_id) DO NOTHING;
```

Zero rows inserted means a duplicate: skip it.

## Outbox pattern

- Never write to the database and publish to the broker as two separate steps: one will fail alone.
- Write the business row and an `outbox` row in one transaction. A relay (polling with `FOR UPDATE SKIP LOCKED`, or CDC with Debezium) publishes and marks it sent.
- The relay is at-least-once too: consumers stay idempotent.

## Producers

- Kafka producer defaults are `acks=all` and `enable.idempotence=true`; keep them. Idempotence needs `max.in.flight.requests.per.connection <= 5` and `retries > 0`.
- Topics: replication factor 3 and `min.insync.replicas=2` in production.
- RabbitMQ: publisher confirms on, persistent messages, quorum queues for anything you cannot lose.

## Ordering

- Kafka orders within a partition only. Use the entity ID as the key so one entity's events stay in order.
- Changing the partition count remaps keys: plan it like a migration.
- RabbitMQ keeps order per queue for a single consumer; competing consumers or redelivery break it. Design handlers so order does not matter, or use a version check.

## Retries, backoff, dead letters

- Retry transient errors with exponential backoff and jitter, with a max attempt count. Do not retry validation errors.
- Kafka: do not block the partition forever. Send failures to retry topics with delays, then to a DLQ topic. Share groups have built-in DLQ support from `share.version=2`.
- RabbitMQ: quorum queues default to a delivery limit of 20 since 4.0; past it the message is dropped unless a dead-letter exchange is set. Always set `dead-letter-exchange` by policy.
- Every DLQ has an owner, an alert and a replay procedure.

## Schemas and contracts

- Payloads have a schema (Avro, Protobuf or JSON Schema) in a registry: Confluent Schema Registry or Apicurio Registry.
- Enforce compatibility (`BACKWARD` or stricter) in CI and in the registry. Add optional fields; never rename or reuse fields.
- Include `messageId`, `type`, `version`, `occurredAt` and a correlation ID in headers or envelope.
- Never put secrets or personal data in payloads or headers unless the topic is classified and encrypted for it. Do not log payloads.

## Security

- TLS everywhere, SASL or mTLS auth, ACLs per service with least privilege (produce or consume on named topics or queues only).

## Tests

- Testcontainers Kafka (`apache/kafka` image) and RabbitMQ modules with the production version.
- Test duplicate delivery, poison message to DLQ, and redelivery after a crash between side effect and ack.
