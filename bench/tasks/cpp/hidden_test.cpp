#include <cstddef>
#include <iostream>
#include <optional>
#include <source_location>
#include <stdexcept>
#include <string>

#include "lru_cache.hpp"

namespace {

int failures = 0;

void check(bool condition, std::source_location where = std::source_location::current()) {
    if (!condition) {
        std::cerr << "hidden_test.cpp:" << where.line() << ": check failed in " << where.function_name() << '\n';
        ++failures;
    }
}

void test_zero_capacity_throws_invalid_argument() {
    bool thrown = false;
    try {
        const lru::Cache<int, std::string> cache(0);
        check(cache.capacity() == 0);
    } catch (const std::invalid_argument&) {
        thrown = true;
    }
    check(thrown);
}

void test_get_returns_the_stored_value_or_nullopt() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    check(cache.get(1) == std::optional<std::string>("one"));
    check(cache.get(2) == std::nullopt);
    check(cache.size() == 1);
    check(cache.capacity() == 2);
}

void test_inserting_into_a_full_cache_evicts_the_least_recently_used() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    cache.put(2, "two");
    cache.put(3, "three");
    check(!cache.contains(1));
    check(cache.contains(2));
    check(cache.contains(3));
    check(cache.size() == 2);
}

void test_get_makes_the_entry_most_recently_used() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    cache.put(2, "two");
    check(cache.get(1).has_value());
    cache.put(3, "three");
    check(cache.contains(1));
    check(!cache.contains(2));
}

void test_contains_does_not_change_the_recency_order() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    cache.put(2, "two");
    check(cache.contains(1));
    cache.put(3, "three");
    check(!cache.contains(1));
    check(cache.contains(2));
}

void test_replacing_a_key_in_a_full_cache_evicts_nothing() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    cache.put(2, "two");
    cache.put(1, "uno");
    check(cache.size() == 2);
    check(cache.get(1) == std::optional<std::string>("uno"));
    check(cache.get(2) == std::optional<std::string>("two"));
}

void test_replacing_a_key_makes_it_most_recently_used() {
    lru::Cache<int, std::string> cache(2);
    cache.put(1, "one");
    cache.put(2, "two");
    cache.put(1, "uno");
    cache.put(3, "three");
    check(cache.contains(1));
    check(!cache.contains(2));
    check(cache.contains(3));
}

void test_capacity_one_keeps_only_the_last_key() {
    lru::Cache<std::string, int> cache(1);
    cache.put("a", 1);
    cache.put("b", 2);
    check(cache.size() == 1);
    check(cache.get("a") == std::nullopt);
    check(cache.get("b") == std::optional<int>(2));
}

void test_many_insertions_stay_within_capacity() {
    constexpr std::size_t capacity = 3;
    constexpr int insertions = 100;
    lru::Cache<int, int> cache(capacity);
    for (int key = 0; key < insertions; ++key) {
        cache.put(key, key * 2);
    }
    check(cache.size() == capacity);
    check(cache.get(insertions - 1) == std::optional<int>((insertions - 1) * 2));
    check(!cache.contains(insertions - 4));
}

}  // namespace

int main() {
    test_zero_capacity_throws_invalid_argument();
    test_get_returns_the_stored_value_or_nullopt();
    test_inserting_into_a_full_cache_evicts_the_least_recently_used();
    test_get_makes_the_entry_most_recently_used();
    test_contains_does_not_change_the_recency_order();
    test_replacing_a_key_in_a_full_cache_evicts_nothing();
    test_replacing_a_key_makes_it_most_recently_used();
    test_capacity_one_keeps_only_the_last_key();
    test_many_insertions_stay_within_capacity();
    return failures == 0 ? 0 : 1;
}
