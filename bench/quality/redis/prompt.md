Write a Python 3.13 module `cache.py` using redis-py that caches the result of an async function with `@cached(ttl_seconds: int, key_prefix: str)`, stores values as JSON, avoids a cache stampede with a short Redis lock, and treats Redis being down as a cache miss (the function still runs).

Work autonomously: nobody will answer questions.
