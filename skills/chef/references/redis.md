# Redis and Valkey

Verified November 2026: Redis Open Source 8.10.x, Valkey 9.1.x. Check current versions on https://github.com/redis/redis/releases and https://github.com/valkey-io/valkey/releases.

## Which one

- Valkey: Linux Foundation fork of Redis 7.2, BSD-3-Clause. Valkey 9.0 added hash field expiration, atomic slot migration and multiple databases in cluster mode.
- Redis 8 and later: tri-licensed RSALv2, SSPLv1 or AGPLv3 (7.4 to 7.8: RSALv2 or SSPLv1 only; 7.2 and earlier: BSD).
- Both speak the same protocol for core commands. Do not rely on module-only features (JSON, search) without checking the target engine supports them.
- Ask the user which engine and license their deployment uses before you pick features.

## Use cases

- Good: cache, sessions, rate limits, locks with a TTL, leaderboards, short-lived queues, pub/sub fan-out.
- Not a system of record. Anything you cannot rebuild lives in the database.
- Durable work queues: use Streams with consumer groups (`XADD`, `XREADGROUP`, `XACK`), or a real broker (see `messaging.md`).

## Keys and TTLs

- Key names: `<app>:<entity>:<id>[:<field>]`, e.g. `shop:cart:42`. Lowercase, colon-separated, documented in one place.
- Every cache key gets a TTL (`SET key value EX 300`). Add jitter so keys do not expire together.
- Never put secrets, tokens or personal data in key names: they show up in `MONITOR`, `SCAN` and logs.
- `SCAN` with `COUNT`, never `KEYS *` in production.
- Avoid big keys: split hashes, lists and sets above a few thousand elements or a few MB.

```python
CACHE_TTL_SECONDS: int = 300
TTL_JITTER_SECONDS: int = 30  # spreads expiries so keys do not all miss at once

def get_user(user_id: int) -> User:
    key: str = f"shop:user:{user_id}"
    cached: bytes | None = redis.get(key)
    if cached is not None:
        return User.model_validate_json(cached)
    user: User = repo.load_user(user_id)
    redis.set(key, user.model_dump_json(), ex=CACHE_TTL_SECONDS + random.randint(0, TTL_JITTER_SECONDS))
    return user
```

## Memory and eviction

- Set `maxmemory`. The default `maxmemory-policy` is `noeviction` (writes fail when full): right for queues and locks, wrong for a cache.
- Cache: `allkeys-lru` or `allkeys-lfu`. `volatile-*` policies act like `noeviction` when no key has a TTL.
- With replication or persistence, leave RAM headroom for replica and AOF buffers.
- Watch `evicted_keys`, `expired_keys` and hit ratio from `INFO stats`.

## Data structures

- Hash for objects, sorted set for rankings and time windows, set for membership, HyperLogLog for approximate counts, Stream for event logs.
- Store values as a stable format (JSON or MessagePack) with a version field.

## Scripts: Lua vs functions

- Use a script only when several commands must be atomic and `MULTI`/`EXEC` is not enough.
- Prefer functions (`FUNCTION LOAD`, `FCALL`): they are persisted and replicated with the data. `EVAL` scripts are ephemeral and must be reloaded by the client.
- Pass every key through `KEYS`, never build key names inside the script: cluster routing needs them.
- Keep scripts short: they block the server while they run.

## Persistence and cluster

- Cache only: persistence off or RDB snapshots. State you care about: AOF `appendfsync everysec` plus RDB.
- High availability: Sentinel for one primary, Cluster for sharding. Multi-key commands in Cluster need a hash tag: `{cart:42}:items`, `{cart:42}:total`.
- Require auth and TLS; use ACL users per app with least privilege. Disable or rename `FLUSHALL`, `CONFIG`, `DEBUG` for app users.

## Tests

- Testcontainers with the same image and major version as production (`redis:8.x` or `valkey/valkey:9.x`).
- Test TTL expiry, eviction behavior under `maxmemory` and the cache-miss path.
