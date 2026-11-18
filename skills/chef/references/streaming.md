# Stream processing: Kafka Streams, Flink

Builds on `messaging.md` (delivery, schemas, DLQs) and `java.md`. Checked November 2026: Kafka 4.4 (see `messaging.md`), Flink 2.3 (announced June 2026). Check `https://kafka.apache.org/downloads` and `https://flink.apache.org/downloads/`.

## Time and windows

- Window on event time, never processing time, unless the logic is about arrival.
- Bound lateness explicitly: Kafka Streams grace period, Flink watermarks with bounded out-of-orderness. Route late events to a side output or count them; never drop them silently.
- Mark idle sources (`withIdleness`) so one quiet partition does not stall watermarks.

## State and delivery

- Exactly-once inside the processor needs: Kafka Streams `processing.guarantee=exactly_once_v2`; Flink exactly-once checkpoints plus a transactional Kafka sink. Downstream consumers read with `isolation.level=read_committed`.
- Side effects outside Kafka (databases, HTTP) stay idempotent: exactly-once does not cover them.
- Give state a TTL or retention; unbounded keyed state grows forever. Large state goes in RocksDB.

## Kafka Streams

- Name every source, processor and state store, so internal topic names survive topology changes.
- Explicit serdes on every operation; do not rely on default serdes.
- Set `num.standby.replicas` for fast failover of stateful tasks.

```java
private static final Duration WINDOW_SIZE = Duration.ofMinutes(5);
private static final Duration GRACE_PERIOD = Duration.ofSeconds(30);

StreamsBuilder builder = new StreamsBuilder();
KStream<String, Order> orders = builder.stream(
    ORDERS_TOPIC, Consumed.with(Serdes.String(), orderSerde).withName("orders-source"));
KTable<Windowed<String>, Long> ordersPerCustomer = orders
    .groupByKey(Grouped.with("orders-by-customer", Serdes.String(), orderSerde))
    .windowedBy(TimeWindows.ofSizeAndGrace(WINDOW_SIZE, GRACE_PERIOD))
    .count(Named.as("count-orders"), Materialized.as("orders-per-customer-store"));
```

- Test topologies with `TopologyTestDriver`: no broker, deterministic time.

## Flink

- Flink 2.x removed the DataSet API, the Scala APIs and `SourceFunction`. Use `env.fromSource(...)` with a `WatermarkStrategy`, and FLIP-27 sources and sinks.
- Set a stable `.uid(...)` on every stateful operator so savepoints restore after code changes. Upgrade by stop-with-savepoint, then start from it.
- Enable checkpointing with an explicit interval, mode and timeout from config.

```java
WatermarkStrategy<Order> watermarks = WatermarkStrategy
    .<Order>forBoundedOutOfOrderness(MAX_OUT_OF_ORDERNESS)
    .withTimestampAssigner((Order order, long recordTimestamp) -> order.createdAtMillis())
    .withIdleness(SOURCE_IDLE_TIMEOUT);
DataStream<Order> orders = env
    .fromSource(orderSource, watermarks, "orders-source")
    .uid("orders-source");
```

- Keep business logic in plain functions tested with JUnit; test operators with Flink's test harnesses and jobs with `MiniClusterExtension`.

## Operations

- Alert on consumer lag, checkpoint duration and failures, backpressure and restarts.
- Never log record payloads; log keys only if they are not personal data.
