#include "ringbuf.h"

ringbuf_status ringbuf_init(ringbuf *buffer, uint8_t *storage, size_t capacity) {
    if (buffer == NULL || storage == NULL || capacity == 0U) {
        return RINGBUF_INVALID;
    }
    buffer->storage = storage;
    buffer->capacity = capacity;
    buffer->head = 0U;
    buffer->count = 0U;
    return RINGBUF_OK;
}

ringbuf_status ringbuf_write(ringbuf *buffer, const uint8_t *data, size_t length) {
    if (buffer == NULL || (data == NULL && length > 0U)) {
        return RINGBUF_INVALID;
    }
    /* Compared against the free space so that a huge length cannot wrap the sum around. */
    if (length > buffer->capacity - buffer->count) {
        return RINGBUF_FULL;
    }
    for (size_t index = 0U; index < length; index++) {
        size_t tail = (buffer->head + buffer->count) % buffer->capacity;
        buffer->storage[tail] = data[index];
        buffer->count++;
    }
    return RINGBUF_OK;
}

ringbuf_status ringbuf_read(ringbuf *buffer, uint8_t *byte) {
    if (buffer == NULL || byte == NULL) {
        return RINGBUF_INVALID;
    }
    if (buffer->count == 0U) {
        return RINGBUF_EMPTY;
    }
    *byte = buffer->storage[buffer->head];
    buffer->head = (buffer->head + 1U) % buffer->capacity;
    buffer->count--;
    return RINGBUF_OK;
}

size_t ringbuf_count(const ringbuf *buffer) {
    return buffer == NULL ? 0U : buffer->count;
}
