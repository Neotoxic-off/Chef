#pragma once

#include <chrono>
#include <cstdint>

namespace ratelimit {

/// A token bucket that refills continuously; the caller passes the current time to every call.
class TokenBucket {
 public:
  using Clock = std::chrono::steady_clock;

  /// Starts full. Throws std::invalid_argument when a setting is 0 or above 1'000'000'000.
  TokenBucket(std::uint64_t capacity, std::uint64_t tokens_per_second, Clock::time_point now);

  /// Takes all the tokens or none. Throws std::invalid_argument, changing nothing, when tokens exceed the capacity.
  [[nodiscard]] bool try_acquire(std::uint64_t tokens, Clock::time_point now);

  /// Whole tokens available at `now`.
  [[nodiscard]] std::uint64_t available(Clock::time_point now);

 private:
  void refill(Clock::time_point now);

  std::uint64_t capacity_;
  std::uint64_t tokens_per_second_;
  std::uint64_t nanotokens_;
  Clock::time_point latest_;
};

}  // namespace ratelimit
