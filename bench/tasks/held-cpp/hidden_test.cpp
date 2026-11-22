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

void check(bool condition, std::source_location where = std::source_location::current()) {
    if (!condition) {
        std::cerr << "hidden_test.cpp:" << where.line() << ": check failed in " << where.function_name() << '\n';
        ++failures;
    }
}

bool construction_throws_invalid_argument(std::uint64_t capacity, std::uint64_t tokens_per_second) {
    try {
        const ratelimit::TokenBucket bucket(capacity, tokens_per_second, start);
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

void test_out_of_range_settings_throw_invalid_argument() {
    check(construction_throws_invalid_argument(0, 1));
    check(construction_throws_invalid_argument(1, 0));
    check(construction_throws_invalid_argument(largest + 1, 1));
    check(construction_throws_invalid_argument(1, largest + 1));
    check(!construction_throws_invalid_argument(largest, largest));
}

void test_a_new_bucket_is_full() {
    ratelimit::TokenBucket bucket(5, 1, start);
    check(bucket.available(start) == 5);
}

void test_acquire_takes_tokens_or_nothing() {
    ratelimit::TokenBucket bucket(5, 1, start);
    check(bucket.try_acquire(3, start));
    check(!bucket.try_acquire(3, start));
    check(bucket.available(start) == 2);
}

void test_acquire_of_the_whole_capacity_succeeds_when_full() {
    ratelimit::TokenBucket bucket(4, 1, start);
    check(bucket.try_acquire(4, start));
    check(bucket.available(start) == 0);
}

void test_acquire_above_the_capacity_throws_and_changes_nothing() {
    ratelimit::TokenBucket bucket(4, 1, start);
    bool thrown = false;
    try {
        static_cast<void>(bucket.try_acquire(5, start));
    } catch (const std::invalid_argument&) {
        thrown = true;
    }
    check(thrown);
    check(bucket.available(start) == 4);
}

void test_a_throwing_acquire_neither_refills_nor_moves_the_time() {
    ratelimit::TokenBucket bucket(4, 1, start);
    check(bucket.try_acquire(4, start));
    bool thrown = false;
    try {
        static_cast<void>(bucket.try_acquire(5, start + 1s));
    } catch (const std::invalid_argument&) {
        thrown = true;
    }
    check(thrown);
    check(bucket.available(start + 500ms) == 0);
    check(bucket.available(start + 1s) == 1);
}

void test_acquire_of_zero_tokens_succeeds_on_an_empty_bucket() {
    ratelimit::TokenBucket bucket(2, 1, start);
    check(bucket.try_acquire(2, start));
    check(bucket.try_acquire(0, start));
    check(bucket.available(start) == 0);
}

void test_tokens_refill_at_the_rate() {
    ratelimit::TokenBucket bucket(10, 2, start);
    check(bucket.try_acquire(10, start));
    check(bucket.available(start + 1s) == 2);
    check(bucket.available(start + 2500ms) == 5);
}

void test_partial_refills_accumulate_between_calls() {
    ratelimit::TokenBucket bucket(1, 1, start);
    check(bucket.try_acquire(1, start));
    check(!bucket.try_acquire(1, start + 600ms));
    check(bucket.available(start + 900ms) == 0);
    check(bucket.try_acquire(1, start + 1200ms));
}

void test_refill_stops_at_the_capacity() {
    ratelimit::TokenBucket bucket(3, 1, start);
    check(bucket.try_acquire(3, start));
    check(bucket.available(start + 1h) == 3);
}

void test_refill_at_the_largest_settings_after_a_long_idle_is_exact() {
    ratelimit::TokenBucket bucket(largest, largest, start);
    check(bucket.try_acquire(largest, start));
    check(bucket.available(start + 1ns) == 1);
    check(bucket.available(start + 24h) == largest);
}

void test_an_earlier_time_adds_nothing_and_keeps_the_latest_time() {
    ratelimit::TokenBucket bucket(1, 1, start);
    check(bucket.try_acquire(1, start + 10s));
    check(!bucket.try_acquire(1, start + 5s));
    check(!bucket.try_acquire(1, start + 10500ms));
    check(bucket.try_acquire(1, start + 11s));
}

void test_available_at_an_earlier_time_adds_nothing() {
    ratelimit::TokenBucket bucket(1, 1, start);
    check(bucket.try_acquire(1, start + 10s));
    check(bucket.available(start + 5s) == 0);
    check(bucket.available(start + 10500ms) == 0);
    check(bucket.available(start + 11s) == 1);
}

}  // namespace

int main() {
    test_out_of_range_settings_throw_invalid_argument();
    test_a_new_bucket_is_full();
    test_acquire_takes_tokens_or_nothing();
    test_acquire_of_the_whole_capacity_succeeds_when_full();
    test_acquire_above_the_capacity_throws_and_changes_nothing();
    test_a_throwing_acquire_neither_refills_nor_moves_the_time();
    test_acquire_of_zero_tokens_succeeds_on_an_empty_bucket();
    test_tokens_refill_at_the_rate();
    test_partial_refills_accumulate_between_calls();
    test_refill_stops_at_the_capacity();
    test_refill_at_the_largest_settings_after_a_long_idle_is_exact();
    test_an_earlier_time_adds_nothing_and_keeps_the_latest_time();
    test_available_at_an_earlier_time_adds_nothing();
    return failures == 0 ? 0 : 1;
}
