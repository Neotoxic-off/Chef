#include "token_bucket.hpp"

#include <stdexcept>
#include <string>

namespace ratelimit {

namespace {

constexpr std::uint64_t max_setting = 1'000'000'000;
// One nanosecond at any rate refills a whole number of nanotokens, so the level stays exact.
constexpr std::uint64_t nanotokens_per_token = 1'000'000'000;

std::uint64_t checked_setting(std::uint64_t value, const char* name) {
  if (value == 0 || value > max_setting) {
    throw std::invalid_argument(std::string("ratelimit::TokenBucket ") + name + " must be in [1, 1000000000], got " +
                                std::to_string(value));
  }
  return value;
}

}  // namespace

TokenBucket::TokenBucket(std::uint64_t capacity, std::uint64_t tokens_per_second, Clock::time_point now)
    : capacity_{checked_setting(capacity, "capacity")},
      tokens_per_second_{checked_setting(tokens_per_second, "tokens_per_second")},
      nanotokens_{capacity_ * nanotokens_per_token},
      latest_{now} {}

bool TokenBucket::try_acquire(std::uint64_t tokens, Clock::time_point now) {
  if (tokens > capacity_) {
    throw std::invalid_argument("ratelimit::TokenBucket::try_acquire: " + std::to_string(tokens) +
                                " tokens exceed the capacity of " + std::to_string(capacity_));
  }
  refill(now);
  const std::uint64_t needed = tokens * nanotokens_per_token;
  if (needed > nanotokens_) {
    return false;
  }
  nanotokens_ -= needed;
  return true;
}

std::uint64_t TokenBucket::available(Clock::time_point now) {
  refill(now);
  return nanotokens_ / nanotokens_per_token;
}

void TokenBucket::refill(Clock::time_point now) {
  if (now <= latest_) {
    return;
  }
  const auto elapsed = static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(now - latest_).count());
  latest_ = now;
  const std::uint64_t full = capacity_ * nanotokens_per_token;
  // Compare before multiplying: elapsed * rate overflows after a long idle period.
  if (elapsed > (full - nanotokens_) / tokens_per_second_) {
    nanotokens_ = full;
    return;
  }
  nanotokens_ += elapsed * tokens_per_second_;
}

}  // namespace ratelimit
