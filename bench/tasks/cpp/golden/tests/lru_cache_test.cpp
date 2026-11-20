#include <iostream>
#include <optional>
#include <source_location>
#include <stdexcept>
#include <string>

#include "lru_cache.hpp"

namespace {

int failures = 0;

void expect(bool condition, std::source_location where = std::source_location::current()) {
  if (!condition) {
    std::cerr << "FAIL: " << where.function_name() << " line " << where.line() << '\n';
    ++failures;
  }
}

void constructor_with_zero_capacity_throws_invalid_argument() {
  bool thrown = false;
  try {
    const lru::Cache<int, int> cache(0);
  } catch (const std::invalid_argument&) {
    thrown = true;
  }
  expect(thrown);
}

void get_of_a_missing_key_returns_nullopt() {
  lru::Cache<int, int> cache(1);
  expect(cache.get(1) == std::nullopt);
}

void put_into_a_full_cache_evicts_the_least_recently_used() {
  lru::Cache<int, std::string> cache(2);
  cache.put(1, "one");
  cache.put(2, "two");
  cache.put(3, "three");
  expect(!cache.contains(1));
  expect(cache.size() == 2);
}

void get_protects_the_entry_from_eviction() {
  lru::Cache<int, std::string> cache(2);
  cache.put(1, "one");
  cache.put(2, "two");
  expect(cache.get(1) == std::optional<std::string>("one"));
  cache.put(3, "three");
  expect(cache.contains(1));
  expect(!cache.contains(2));
}

void contains_does_not_protect_the_entry_from_eviction() {
  lru::Cache<int, std::string> cache(2);
  cache.put(1, "one");
  cache.put(2, "two");
  expect(cache.contains(1));
  cache.put(3, "three");
  expect(!cache.contains(1));
}

void put_of_an_existing_key_replaces_without_evicting() {
  lru::Cache<int, std::string> cache(2);
  cache.put(1, "one");
  cache.put(2, "two");
  cache.put(1, "uno");
  expect(cache.size() == 2);
  expect(cache.get(1) == std::optional<std::string>("uno"));
  expect(cache.contains(2));
}

void put_of_an_existing_key_protects_it_from_eviction() {
  lru::Cache<int, std::string> cache(2);
  cache.put(1, "one");
  cache.put(2, "two");
  cache.put(1, "uno");
  cache.put(3, "three");
  expect(cache.contains(1));
  expect(!cache.contains(2));
}

}  // namespace

int main() {
  constructor_with_zero_capacity_throws_invalid_argument();
  get_of_a_missing_key_returns_nullopt();
  put_into_a_full_cache_evicts_the_least_recently_used();
  get_protects_the_entry_from_eviction();
  contains_does_not_protect_the_entry_from_eviction();
  put_of_an_existing_key_replaces_without_evicting();
  put_of_an_existing_key_protects_it_from_eviction();
  return failures == 0 ? 0 : 1;
}
