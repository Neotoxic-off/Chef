#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "ringbuf.h"

static int failures = 0;

static void check(int condition, const char *expression, int line) {
    if (!condition) {
        (void)fprintf(stderr, "hidden_test.c:%d: check failed: %s\n", line, expression);
        failures++;
    }
}

#define CHECK(expression) check((expression) ? 1 : 0, #expression, __LINE__)

static void test_init_rejects_null_and_zero_capacity(void) {
    ringbuf buffer;
    uint8_t storage[4] = {0};
    CHECK(ringbuf_init(NULL, storage, sizeof storage) == RINGBUF_INVALID);
    CHECK(ringbuf_init(&buffer, NULL, sizeof storage) == RINGBUF_INVALID);
    CHECK(ringbuf_init(&buffer, storage, 0U) == RINGBUF_INVALID);
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_count(&buffer) == 0U);
    CHECK(ringbuf_count(NULL) == 0U);
}

static void test_reads_bytes_in_write_order(void) {
    ringbuf buffer;
    uint8_t storage[4] = {0};
    const uint8_t data[3] = {10U, 20U, 30U};
    uint8_t byte = 0U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, data, sizeof data) == RINGBUF_OK);
    CHECK(ringbuf_count(&buffer) == 3U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 10U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 20U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 30U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_EMPTY);
    CHECK(ringbuf_count(&buffer) == 0U);
}

static void test_every_byte_of_capacity_is_usable(void) {
    ringbuf buffer;
    uint8_t storage[4] = {0};
    const uint8_t data[4] = {1U, 2U, 3U, 4U};
    const uint8_t extra = 5U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, data, sizeof data) == RINGBUF_OK);
    CHECK(ringbuf_count(&buffer) == 4U);
    CHECK(ringbuf_write(&buffer, &extra, 1U) == RINGBUF_FULL);
    CHECK(ringbuf_count(&buffer) == 4U);
}

static void test_write_is_all_or_nothing(void) {
    ringbuf buffer;
    uint8_t storage[4] = {0};
    const uint8_t first[2] = {1U, 2U};
    const uint8_t second[3] = {7U, 8U, 9U};
    uint8_t byte = 0U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, first, sizeof first) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, second, sizeof second) == RINGBUF_FULL);
    CHECK(ringbuf_count(&buffer) == 2U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 1U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 2U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_EMPTY);
}

static void test_huge_length_is_full_not_an_overflow(void) {
    ringbuf buffer;
    uint8_t storage[4] = {0};
    const uint8_t data[1] = {42U};
    uint8_t byte = 0U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, data, sizeof data) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, data, SIZE_MAX) == RINGBUF_FULL);
    CHECK(ringbuf_write(&buffer, data, SIZE_MAX - 1U) == RINGBUF_FULL);
    CHECK(ringbuf_count(&buffer) == 1U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 42U);
}

static void test_wraps_around_the_end_of_storage(void) {
    ringbuf buffer;
    uint8_t storage[3] = {0};
    const uint8_t first[3] = {1U, 2U, 3U};
    const uint8_t second[2] = {4U, 5U};
    uint8_t byte = 0U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, first, sizeof first) == RINGBUF_OK);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 1U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 2U);
    CHECK(ringbuf_write(&buffer, second, sizeof second) == RINGBUF_OK);
    CHECK(ringbuf_count(&buffer) == 3U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 3U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 4U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_OK && byte == 5U);
    CHECK(ringbuf_read(&buffer, &byte) == RINGBUF_EMPTY);
}

static void test_null_arguments_are_invalid(void) {
    ringbuf buffer;
    uint8_t storage[2] = {0};
    const uint8_t data[1] = {1U};
    uint8_t byte = 0U;
    CHECK(ringbuf_init(&buffer, storage, sizeof storage) == RINGBUF_OK);
    CHECK(ringbuf_write(NULL, data, sizeof data) == RINGBUF_INVALID);
    CHECK(ringbuf_write(&buffer, NULL, 1U) == RINGBUF_INVALID);
    CHECK(ringbuf_write(&buffer, NULL, 0U) == RINGBUF_OK);
    CHECK(ringbuf_write(&buffer, data, 0U) == RINGBUF_OK);
    CHECK(ringbuf_count(&buffer) == 0U);
    CHECK(ringbuf_read(NULL, &byte) == RINGBUF_INVALID);
    CHECK(ringbuf_read(&buffer, NULL) == RINGBUF_INVALID);
}

int main(void) {
    test_init_rejects_null_and_zero_capacity();
    test_reads_bytes_in_write_order();
    test_every_byte_of_capacity_is_usable();
    test_write_is_all_or_nothing();
    test_huge_length_is_full_not_an_overflow();
    test_wraps_around_the_end_of_storage();
    test_null_arguments_are_invalid();
    return failures == 0 ? 0 : 1;
}
