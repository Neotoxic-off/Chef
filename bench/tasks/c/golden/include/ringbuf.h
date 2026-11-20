#ifndef RINGBUF_H
#define RINGBUF_H

#include <stddef.h>
#include <stdint.h>

/* A fixed-capacity FIFO of bytes over caller-provided storage; it never allocates. */
typedef struct {
    uint8_t *storage;
    size_t capacity;
    size_t head;
    size_t count;
} ringbuf;

typedef enum {
    RINGBUF_OK = 0,
    RINGBUF_INVALID,
    RINGBUF_FULL,
    RINGBUF_EMPTY
} ringbuf_status;

/* RINGBUF_INVALID for a null buffer or storage or a zero capacity. */
ringbuf_status ringbuf_init(ringbuf *buffer, uint8_t *storage, size_t capacity);

/* Appends all length bytes, or none and RINGBUF_FULL when fewer are free. */
ringbuf_status ringbuf_write(ringbuf *buffer, const uint8_t *data, size_t length);

/* Removes the oldest byte into *byte; RINGBUF_EMPTY when there is none. */
ringbuf_status ringbuf_read(ringbuf *buffer, uint8_t *byte);

/* The number of bytes stored, 0 for a null buffer. */
size_t ringbuf_count(const ringbuf *buffer);

#endif
