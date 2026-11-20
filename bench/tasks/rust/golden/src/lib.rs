//! Strict `MAJOR.MINOR.PATCH` version parsing and comparison.

use std::cmp::Ordering;
use std::fmt;

const PART_COUNT: usize = 3;
const VERSION_PREFIX: &str = "v";

/// A parsed version; field order makes the derived ordering part-by-part.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Version {
    pub major: u64,
    pub minor: u64,
    pub patch: u64,
}

/// Why a version string is invalid.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VersionError {
    WrongPartCount { found: usize },
    EmptyPart { index: usize },
    NonDigit { index: usize },
    LeadingZero { index: usize },
    OutOfRange { index: usize },
}

impl fmt::Display for VersionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::WrongPartCount { found } => {
                write!(
                    formatter,
                    "expected {PART_COUNT} parts separated by dots, found {found}"
                )
            }
            Self::EmptyPart { index } => write!(formatter, "part {} is empty", index + 1),
            Self::NonDigit { index } => {
                write!(
                    formatter,
                    "part {} contains a character that is not a digit",
                    index + 1
                )
            }
            Self::LeadingZero { index } => {
                write!(formatter, "part {} has a leading zero", index + 1)
            }
            Self::OutOfRange { index } => {
                write!(
                    formatter,
                    "part {} does not fit in an unsigned 64-bit integer",
                    index + 1
                )
            }
        }
    }
}

impl std::error::Error for VersionError {}

fn parse_part(text: &str, index: usize) -> Result<u64, VersionError> {
    if text.is_empty() {
        return Err(VersionError::EmptyPart { index });
    }
    if !text.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(VersionError::NonDigit { index });
    }
    if text.len() > 1 && text.starts_with('0') {
        return Err(VersionError::LeadingZero { index });
    }
    text.parse().map_err(|_| VersionError::OutOfRange { index })
}

/// Parses `[v]MAJOR.MINOR.PATCH`.
///
/// # Errors
///
/// Returns the first rule the text breaks.
pub fn parse_version(text: &str) -> Result<Version, VersionError> {
    let numbers = text.strip_prefix(VERSION_PREFIX).unwrap_or(text);
    let parts: Vec<&str> = numbers.split('.').collect();
    let [major, minor, patch] = parts[..] else {
        return Err(VersionError::WrongPartCount { found: parts.len() });
    };
    Ok(Version {
        major: parse_part(major, 0)?,
        minor: parse_part(minor, 1)?,
        patch: parse_part(patch, 2)?,
    })
}

/// Compares two versions, or returns `None` when either is invalid.
#[must_use]
pub fn compare_versions(left: &str, right: &str) -> Option<Ordering> {
    let left = parse_version(left).ok()?;
    let right = parse_version(right).ok()?;
    Some(left.cmp(&right))
}

#[cfg(test)]
mod tests {
    use super::*;

    const MAX: &str = "18446744073709551615";

    #[test]
    fn compare_versions_compares_numerically_not_textually() {
        assert_eq!(compare_versions("1.10.0", "1.9.0"), Some(Ordering::Greater));
    }

    #[test]
    fn compare_versions_checks_each_part_in_order() {
        assert_eq!(compare_versions("2.0.0", "1.9.9"), Some(Ordering::Greater));
        assert_eq!(compare_versions("1.2.9", "1.3.0"), Some(Ordering::Less));
        assert_eq!(compare_versions("1.2.3", "1.2.4"), Some(Ordering::Less));
    }

    #[test]
    fn compare_versions_ignores_v_prefix() {
        assert_eq!(compare_versions("v1.2.3", "1.2.3"), Some(Ordering::Equal));
        assert_eq!(compare_versions("1.2.3", "v1.2.4"), Some(Ordering::Less));
    }

    #[test]
    fn compare_versions_accepts_u64_max_and_zero() {
        let max = format!("{MAX}.{MAX}.{MAX}");
        assert_eq!(compare_versions(&max, "0.0.0"), Some(Ordering::Greater));
    }

    #[test]
    fn compare_versions_with_either_side_invalid_returns_none() {
        assert_eq!(compare_versions("1.2", "1.2.3"), None);
        assert_eq!(compare_versions("1.2.3", "x"), None);
    }

    #[test]
    fn parse_version_rejects_each_invalid_shape() {
        let cases = [
            ("", VersionError::WrongPartCount { found: 1 }),
            ("1.2", VersionError::WrongPartCount { found: 2 }),
            ("1.2.3.4", VersionError::WrongPartCount { found: 4 }),
            ("vv1.2.3", VersionError::NonDigit { index: 0 }),
            ("V1.2.3", VersionError::NonDigit { index: 0 }),
            ("v", VersionError::WrongPartCount { found: 1 }),
            ("1..3", VersionError::EmptyPart { index: 1 }),
            ("1.2.", VersionError::EmptyPart { index: 2 }),
            ("+1.2.3", VersionError::NonDigit { index: 0 }),
            ("1.-2.3", VersionError::NonDigit { index: 1 }),
            (" 1.2.3", VersionError::NonDigit { index: 0 }),
            ("1.2.3 ", VersionError::NonDigit { index: 2 }),
            ("1.2.3-rc1", VersionError::NonDigit { index: 2 }),
            ("1.2.3+build", VersionError::NonDigit { index: 2 }),
            ("1.2.\u{663}", VersionError::NonDigit { index: 2 }),
            ("01.2.3", VersionError::LeadingZero { index: 0 }),
            ("1.2.00", VersionError::LeadingZero { index: 2 }),
            (
                "1.18446744073709551616.3",
                VersionError::OutOfRange { index: 1 },
            ),
        ];
        for (text, expected) in cases {
            assert_eq!(parse_version(text), Err(expected), "input {text:?}");
        }
    }

    #[test]
    fn parse_version_returns_parts() {
        let expected = Version {
            major: 1,
            minor: 20,
            patch: 0,
        };
        assert_eq!(parse_version("v1.20.0"), Ok(expected));
    }

    #[test]
    fn error_messages_name_the_failing_part() {
        let messages = [
            (
                VersionError::WrongPartCount { found: 2 },
                "expected 3 parts separated by dots, found 2",
            ),
            (VersionError::EmptyPart { index: 1 }, "part 2 is empty"),
            (
                VersionError::NonDigit { index: 0 },
                "part 1 contains a character that is not a digit",
            ),
            (
                VersionError::LeadingZero { index: 2 },
                "part 3 has a leading zero",
            ),
            (
                VersionError::OutOfRange { index: 0 },
                "part 1 does not fit in an unsigned 64-bit integer",
            ),
        ];
        for (error, message) in messages {
            assert_eq!(error.to_string(), message);
        }
    }
}
