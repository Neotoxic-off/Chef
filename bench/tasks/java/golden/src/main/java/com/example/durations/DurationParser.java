package com.example.durations;

import java.math.BigInteger;
import java.time.Duration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Parses human-written durations such as {@code 1h30m} or {@code 45s}. */
public final class DurationParser {

  private static final Pattern FORMAT =
      Pattern.compile("(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?");
  private static final BigInteger SECONDS_PER_HOUR = BigInteger.valueOf(3600);
  private static final BigInteger SECONDS_PER_MINUTE = BigInteger.valueOf(60);
  // Longest decimal number that can still fit in a long; longer ones are rejected before parsing.
  private static final int MAX_SIGNIFICANT_DIGITS = 19;

  private DurationParser() {}

  /**
   * Parses hours, minutes and seconds, each optional, in that order (for example {@code 1h30m}).
   *
   * @param text the text to parse
   * @return the parsed duration
   * @throws IllegalArgumentException if the text is null, malformed or too large for a {@link
   *     Duration}
   */
  public static Duration parse(String text) {
    if (text == null) {
      throw new IllegalArgumentException("Duration text must not be null");
    }
    Matcher matcher = FORMAT.matcher(text);
    if (text.isEmpty() || !matcher.matches()) {
      throw new IllegalArgumentException(
          "Invalid duration '%s': expected parts like 1h30m, 90m or 45s".formatted(text));
    }
    BigInteger totalSeconds =
        part(matcher.group(1), SECONDS_PER_HOUR, text)
            .add(part(matcher.group(2), SECONDS_PER_MINUTE, text))
            .add(part(matcher.group(3), BigInteger.ONE, text));
    if (totalSeconds.bitLength() >= Long.SIZE) {
      throw tooLarge(text);
    }
    return Duration.ofSeconds(totalSeconds.longValueExact());
  }

  private static BigInteger part(String digits, BigInteger secondsPerUnit, String text) {
    if (digits == null) {
      return BigInteger.ZERO;
    }
    String significant = digits.replaceFirst("^0+(?=.)", "");
    if (significant.length() > MAX_SIGNIFICANT_DIGITS) {
      throw tooLarge(text);
    }
    return new BigInteger(significant).multiply(secondsPerUnit);
  }

  private static IllegalArgumentException tooLarge(String text) {
    return new IllegalArgumentException("Duration '%s' is too large".formatted(text));
  }
}
