#pragma once

#include <cstddef>
#include <list>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace lru {

/// A fixed-capacity cache that evicts the least recently used entry when a new key does not fit.
template <typename Key, typename Value>
class Cache {
 public:
  /// Throws std::invalid_argument when capacity is 0.
  explicit Cache(std::size_t capacity) : capacity_{capacity} {
    if (capacity == 0) {
      throw std::invalid_argument("lru::Cache capacity must be at least 1");
    }
  }

  /// Inserts or replaces; either way the entry becomes the most recently used.
  void put(const Key& key, Value value) {
    if (const auto found = index_.find(key); found != index_.end()) {
      found->second->second = std::move(value);
      entries_.splice(entries_.begin(), entries_, found->second);
      return;
    }
    if (entries_.size() == capacity_) {
      index_.erase(entries_.back().first);
      entries_.pop_back();
    }
    entries_.emplace_front(key, std::move(value));
    index_.emplace(key, entries_.begin());
  }

  /// The value, now the most recently used, or std::nullopt.
  [[nodiscard]] std::optional<Value> get(const Key& key) {
    const auto found = index_.find(key);
    if (found == index_.end()) {
      return std::nullopt;
    }
    entries_.splice(entries_.begin(), entries_, found->second);
    return found->second->second;
  }

  /// Leaves the recency order unchanged.
  [[nodiscard]] bool contains(const Key& key) const { return index_.contains(key); }

  [[nodiscard]] std::size_t size() const noexcept { return entries_.size(); }

  [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

 private:
  using Entry = std::pair<Key, Value>;
  using Position = typename std::list<Entry>::iterator;

  std::size_t capacity_;
  std::list<Entry> entries_;  // most recently used first
  std::unordered_map<Key, Position> index_;
};

}  // namespace lru
