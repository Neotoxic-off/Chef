#include <chrono>
#include <cstdint>
#include <iostream>
#include <source_location>
#include <stdexcept>

#include "token_bucket.hpp"

namespace {

using Clock = std::chrono::steady_clock;
using namespace std::chrono_literals;

constexpr std::uint64_t largest = 1'000'000'000;
const Clock::time_point start{};

int failures = 0;

void expect(bool condition, std::source_location where = std::source_location::current()) {
  if (!condition) {
    std::cerr << "FAIL: " << where.function_name() << " line " << where.line() << '\n';
    ++failures;
  }
}

bool construction_throws(std::uint64_t capacity, std::uint64_t tokens_per_second) {
  try {
    const ratelimit::TokenBucket bucket(capacity, tokens_per_second, start);
  } catch (const std::invalid_argument&) {
    return true;
  }
  return false;
}

void constructor_with_zero_capacity_throws_invalid_argument() { expect(construction_throws(0, 1)); }

void constructor_with_zero_rate_throws_invalid_argument() { expect(construction_throws(1, 0)); }

void constructor_above_the_largest_settings_throws_invalid_argument() {
  expect(construction_throws(largest + 1, 1));
  expect(construction_throws(1, largest + 1));
}

void constructor_accepts_the_largest_settings() { expect(!construction_throws(largest, largest)); }

void new_bucket_is_full() {
  ratelimit::TokenBucket bucket(3, 1, start);
  expect(bucket.available(start) == 3);
}

void try_acquire_of_the_whole_capacity_empties_the_bucket() {
  ratelimit::TokenBucket bucket(3, 1, start);
  expect(bucket.try_acquire(3, start));
  expect(bucket.available(start) == 0);
}

void try_acquire_with_too_few_tokens_takes_nothing() {
  ratelimit::TokenBucket bucket(3, 1, start);
  expect(bucket.try_acquire(2, start));
  expect(!bucket.try_acquire(2, start));
  expect(bucket.available(start) == 1);
}

void try_acquire_of_zero_tokens_on_an_empty_bucket_succeeds() {
  ratelimit::TokenBucket bucket(1, 1, start);
  expect(bucket.try_acquire(1, start));
  expect(bucket.try_acquire(0, start));
}

void try_acquire_above_the_capacity_throws_and_takes_nothing() {
  ratelimit::TokenBucket bucket(2, 1, start);
  bool thrown = false;
  try {
    static_cast<void>(bucket.try_acquire(3, start));
  } catch (const std::invalid_argument&) {
    thrown = true;
  }
  expect(thrown);
  expect(bucket.available(start) == 2);
}

void refill_follows_the_rate() {
  ratelimit::TokenBucket bucket(10, 4, start);
  expect(bucket.try_acquire(10, start));
  expect(bucket.available(start + 1500ms) == 6);
}

void partial_refills_add_up_across_calls() {
  ratelimit::TokenBucket bucket(1, 1, start);
  expect(bucket.try_acquire(1, start));
  expect(bucket.available(start + 600ms) == 0);
  expect(bucket.available(start + 1200ms) == 1);
}

void refill_stops_at_the_capacity() {
  ratelimit::TokenBucket bucket(2, 1, start);
  expect(bucket.try_acquire(2, start));
  expect(bucket.available(start + 10s) == 2);
}

void refill_after_a_long_idle_at_the_largest_settings_does_not_overflow() {
  ratelimit::TokenBucket bucket(largest, largest, start);
  expect(bucket.try_acquire(largest, start));
  expect(bucket.available(start + 48h) == largest);
}

void earlier_time_adds_nothing_and_does_not_move_time_back() {
  ratelimit::TokenBucket bucket(1, 1, start);
  expect(bucket.try_acquire(1, start + 10s));
  expect(bucket.available(start + 1s) == 0);
  expect(bucket.available(start + 10500ms) == 0);
  expect(bucket.available(start + 11s) == 1);
}

}  // namespace

int main() {
  constructor_with_zero_capacity_throws_invalid_argument();
  constructor_with_zero_rate_throws_invalid_argument();
  constructor_above_the_largest_settings_throws_invalid_argument();
  constructor_accepts_the_largest_settings();
  new_bucket_is_full();
  try_acquire_of_the_whole_capacity_empties_the_bucket();
  try_acquire_with_too_few_tokens_takes_nothing();
  try_acquire_of_zero_tokens_on_an_empty_bucket_succeeds();
  try_acquire_above_the_capacity_throws_and_takes_nothing();
  refill_follows_the_rate();
  partial_refills_add_up_across_calls();
  refill_stops_at_the_capacity();
  refill_after_a_long_idle_at_the_largest_settings_does_not_overflow();
  earlier_time_adds_nothing_and_does_not_move_time_back();
  return failures == 0 ? 0 : 1;
}
