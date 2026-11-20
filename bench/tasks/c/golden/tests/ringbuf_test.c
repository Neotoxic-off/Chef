#include <stdint.h>
#include <stdio.h>

#include "ringbuf.h"

static int failures = 0;

static void expect(int condition, const char *name) {
    if (!condition) {
        (void)fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    }
}

static void init_with_zero_capacity_is_invalid(void) {
    ringbuf buffer;
    uint8_t storage[1] = {0};
    expect(ringbuf_init(&buffer, storage, 0U) == RINGBUF_INVALID, "init with zero capacity is invalid");
}

static void init_with_null_storage_is_invalid(void) {
    ringbuf buffer;
    expect(ringbuf_init(&buffer, NULL, 1U) == RINGBUF_INVALID, "init with null storage is invalid");
}

static void read_from_empty_buffer_is_empty(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    uint8_t byte = 0U;
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    expect(ringbuf_read(&buffer, &byte) == RINGBUF_EMPTY, "read from empty buffer is empty");
}

static void write_fills_the_whole_capacity(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    const uint8_t data[2] = {1U, 2U};
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    expect(ringbuf_write(&buffer, data, sizeof data) == RINGBUF_OK, "write fills the whole capacity");
    expect(ringbuf_count(&buffer) == 2U, "count after filling is the capacity");
}

static void write_past_capacity_writes_nothing(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    const uint8_t data[3] = {1U, 2U, 3U};
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    expect(ringbuf_write(&buffer, data, sizeof data) == RINGBUF_FULL, "write past capacity is full");
    expect(ringbuf_count(&buffer) == 0U, "write past capacity writes nothing");
}

static void write_of_size_max_is_full(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    const uint8_t data[1] = {1U};
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    (void)ringbuf_write(&buffer, data, sizeof data);
    expect(ringbuf_write(&buffer, data, SIZE_MAX) == RINGBUF_FULL, "write of SIZE_MAX is full");
}

static void write_of_null_data_is_invalid(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    expect(ringbuf_write(&buffer, NULL, 1U) == RINGBUF_INVALID, "write of null data is invalid");
}

static void read_returns_bytes_in_order_across_the_wrap(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    const uint8_t first[2] = {1U, 2U};
    const uint8_t second[1] = {3U};
    uint8_t byte = 0U;
    (void)ringbuf_init(&buffer, storage, sizeof storage);
    (void)ringbuf_write(&buffer, first, sizeof first);
    (void)ringbuf_read(&buffer, &byte);
    (void)ringbuf_write(&buffer, second, sizeof second);
    expect(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 2U, "read after wrap returns the older byte");
    expect(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 3U, "read after wrap returns the newer byte");
}

static void count_of_null_buffer_is_zero(void) {
    expect(ringbuf_count(NULL) == 0U, "count of null buffer is zero");
}

int main(void) {
    init_with_zero_capacity_is_invalid();
    init_with_null_storage_is_invalid();
    read_from_empty_buffer_is_empty();
    write_fills_the_whole_capacity();
    write_past_capacity_writes_nothing();
    write_of_size_max_is_full();
    write_of_null_data_is_invalid();
    read_returns_bytes_in_order_across_the_wrap();
    count_of_null_buffer_is_zero();
    return failures == 0 ? 0 : 1;
}
