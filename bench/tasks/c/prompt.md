Create a C17 library in this folder: a fixed-capacity byte ring buffer for a UART driver, built with CMake (CMake 3.31, GCC 14).

Make the folder a CMake project with a library target named `ringbuf`, whose public header `ringbuf.h` is on the target's include path. The header defines `ringbuf` as a complete struct type (callers declare one on the stack and pass the storage; the library never allocates) and the enum `ringbuf_status` with `RINGBUF_OK`, `RINGBUF_INVALID`, `RINGBUF_FULL` and `RINGBUF_EMPTY`, and declares:

- `ringbuf_status ringbuf_init(ringbuf *buffer, uint8_t *storage, size_t capacity)`: `RINGBUF_INVALID` for a null `buffer` or `storage` or a zero `capacity`; all `capacity` bytes are usable.
- `ringbuf_status ringbuf_write(ringbuf *buffer, const uint8_t *data, size_t length)`: appends all `length` bytes or none of them, returning `RINGBUF_FULL` and leaving the buffer unchanged when fewer than `length` bytes are free. `length` can be any `size_t`, `SIZE_MAX` included; a zero `length` is `RINGBUF_OK` and writes nothing; a null `buffer`, or a null `data` with a non-zero `length`, is `RINGBUF_INVALID`.
- `ringbuf_status ringbuf_read(ringbuf *buffer, uint8_t *byte)`: removes the oldest byte into `*byte`, `RINGBUF_EMPTY` when there is none, `RINGBUF_INVALID` for a null argument.
- `size_t ringbuf_count(const ringbuf *buffer)`: the number of bytes stored, 0 for a null `buffer`.

Work autonomously: nobody will answer questions.
