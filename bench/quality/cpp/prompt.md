Write a C++23 header-only library `include/ring_buffer.hpp` with `template <typename T, std::size_t Capacity> class RingBuffer` offering `push` (returns false when full), `pop` (returns `std::optional<T>`), `size`, `empty`, `full`, and iteration from oldest to newest. `Capacity` 0 must not compile. CMake build.

Work autonomously: nobody will answer questions.
