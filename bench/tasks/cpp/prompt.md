Create a C++20 library in this folder: an in-memory LRU cache for a service's lookup results, built with CMake (CMake 3.31, GCC 14).

Make the folder a CMake project with a library target named `lru_cache`, whose public header `lru_cache.hpp` is on the target's include path. In the namespace `lru`, define the class template `template <typename Key, typename Value> class Cache` (keys work with `std::hash` and `==`) with:

- `explicit Cache(std::size_t capacity)`, which throws `std::invalid_argument` when `capacity` is 0;
- `void put(const Key& key, Value value)`, which inserts the entry, or replaces the value of an existing key; inserting a new key into a full cache first evicts the least recently used entry;
- `std::optional<Value> get(const Key& key)`, which returns the value and makes the entry the most recently used, or `std::nullopt`;
- `bool contains(const Key& key) const`, which does not change the recency order;
- `std::size_t size() const noexcept` and `std::size_t capacity() const noexcept`.

Replacing the value of an existing key counts as a use of that entry and never evicts anything.

Work autonomously: nobody will answer questions.
