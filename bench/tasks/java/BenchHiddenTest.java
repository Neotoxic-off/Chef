package com.example.durations;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class BenchHiddenTest {

    @ParameterizedTest
    @CsvSource({
        "1h30m, 5400",
        "45s, 45",
        "90m, 5400",
        "2m5s, 125",
        "1h2m3s, 3723",
        "1h5s, 3605",
        "0s, 0",
        "007m, 420",
    })
    void parse_withValidText_returnsDuration(String text, long expectedSeconds) {
        Duration parsed = DurationParser.parse(text);

        assertEquals(Duration.ofSeconds(expectedSeconds), parsed);
    }

    @Test
    void parse_withNull_throwsIllegalArgumentException() {
        assertThrows(IllegalArgumentException.class, () -> DurationParser.parse(null));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "",
        "   ",
        "1h 30m",
        " 5s",
        "5s\n",
        "-5s",
        "+5s",
        "1.5h",
        "5d",
        "1H",
        "5",
        "h",
        "1h30",
        "30m1h",
        "1m2m",
        "1s1m",
        "9999999999999999999h",
        "9223372036854775807h",
        "9223372036854775807m",
    })
    void parse_withInvalidText_throwsIllegalArgumentException(String text) {
        assertThrows(IllegalArgumentException.class, () -> DurationParser.parse(text));
    }
}
