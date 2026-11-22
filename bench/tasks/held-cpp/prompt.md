Create a C++20 library in this folder: a token-bucket rate limiter for a service's outgoing API calls, built with CMake (CMake 3.31, GCC 14).

Make the folder a CMake project with a library target named `token_bucket`, whose public header `token_bucket.hpp` is on the target's include path. In the namespace `ratelimit`, define the class `TokenBucket`. The caller passes the current time to every call as a `std::chrono::steady_clock::time_point`; the class never reads a clock itself. It has:

- `TokenBucket(std::uint64_t capacity, std::uint64_t tokens_per_second, std::chrono::steady_clock::time_point now)`, which starts full, and throws `std::invalid_argument` when `capacity` or `tokens_per_second` is 0 or above 1'000'000'000;
- `bool try_acquire(std::uint64_t tokens, std::chrono::steady_clock::time_point now)`, which refills, then takes `tokens` and returns `true`, or takes nothing and returns `false` when fewer are available; 0 tokens always succeeds; it throws `std::invalid_argument`, and changes nothing, when `tokens` is above the capacity;
- `std::uint64_t available(std::chrono::steady_clock::time_point now)`, which refills, then returns the number of whole tokens available.

Tokens refill continuously at `tokens_per_second`, up to the capacity, with nanosecond precision: partial tokens are never lost between calls (at 1 token per second, calls 600 ms apart give a whole token on the second call). The refill stays exact after any idle time, even days at the largest capacity and rate. A `now` earlier than the latest one seen adds no tokens and does not move the bucket's time back.

Work autonomously: nobody will answer questions.
