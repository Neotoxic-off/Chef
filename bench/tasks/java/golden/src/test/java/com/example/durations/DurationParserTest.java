package com.example.durations;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullSource;
import org.junit.jupiter.params.provider.ValueSource;

class DurationParserTest {

  @ParameterizedTest
  @ValueSource(
      strings = {"1h30m", "2m5s", "90m", "45s", "1h", "1h1m1s", "0s", "007s", "000s", "1h0m0s"})
  void parse_withValidText_returnsDuration(String text) {
    assertThat(DurationParser.parse(text)).isNotNull();
  }

  @Test
  void parse_withHoursAndMinutes_sumsThem() {
    assertThat(DurationParser.parse("1h30m")).isEqualTo(Duration.ofMinutes(90));
  }

  @Test
  void parse_withMinutesAndSeconds_sumsThem() {
    assertThat(DurationParser.parse("2m5s")).isEqualTo(Duration.ofSeconds(125));
  }

  @Test
  void parse_withMoreThanSixtyMinutes_isAccepted() {
    assertThat(DurationParser.parse("90m")).isEqualTo(Duration.ofMinutes(90));
  }

  @Test
  void parse_withZeroSeconds_returnsZero() {
    assertThat(DurationParser.parse("0s")).isEqualTo(Duration.ZERO);
  }

  @Test
  void parse_withLeadingZeros_ignoresThem() {
    assertThat(DurationParser.parse("0000000000000000000000045s"))
        .isEqualTo(Duration.ofSeconds(45));
  }

  @Test
  void parse_withLargestSecondsValue_returnsMaxSeconds() {
    assertThat(DurationParser.parse("9223372036854775807s"))
        .isEqualTo(Duration.ofSeconds(Long.MAX_VALUE));
  }

  @Test
  void parse_withLargestHoursValueThatFits_succeeds() {
    assertThat(DurationParser.parse("2562047788015215h"))
        .isEqualTo(Duration.ofHours(2562047788015215L));
  }

  @Test
  void parse_withHoursAndSecondsSummingToMax_succeeds() {
    // 2562047788015215h = 9223372036854774000s; 1807s brings the total to Long.MAX_VALUE
    assertThat(DurationParser.parse("2562047788015215h1807s"))
        .isEqualTo(Duration.ofSeconds(Long.MAX_VALUE));
  }

  @ParameterizedTest
  @NullSource
  @ValueSource(
      strings = {
        "", " ", "\t", " 1h", "1h ", "1h 30m", "1h\n", "\n1h", "30m1h", "1m2m", "1h1h", "1s1m",
        "+1h", "-1h", "1.5h", "1,5h", "1d", "1H", "1ms", "5", "1h30", "h", "1hm", "m30s", "1h30mx",
        "x", "٣s",
      })
  void parse_withInvalidText_throwsIllegalArgumentException(String text) {
    assertThatThrownBy(() -> DurationParser.parse(text))
        .isExactlyInstanceOf(IllegalArgumentException.class);
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "9223372036854775808s",
        "2562047788015216h",
        "153722867280912931m",
        "2562047788015215h1808s",
        "99999999999999999999999999999999999999s",
        "9223372036854775807h",
        "9223372036854775807m9223372036854775807s",
      })
  void parse_withTooLargeNumber_throwsIllegalArgumentException(String text) {
    assertThatThrownBy(() -> DurationParser.parse(text))
        .isExactlyInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("too large");
  }

  @Test
  void parse_withNull_explainsWhy() {
    assertThatThrownBy(() -> DurationParser.parse(null))
        .isExactlyInstanceOf(IllegalArgumentException.class)
        .hasMessage("Duration text must not be null");
  }

  @Test
  void parse_withInvalidText_includesTextInMessage() {
    assertThatThrownBy(() -> DurationParser.parse("30m1h"))
        .isExactlyInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("30m1h");
  }
}
