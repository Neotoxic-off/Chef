use std::cmp::Ordering;

use versions::compare_versions;

const ORDERED: [(&str, &str, Ordering); 7] = [
    ("1.2.3", "1.2.3", Ordering::Equal),
    ("v1.2.3", "1.2.3", Ordering::Equal),
    ("1.10.0", "1.9.0", Ordering::Greater),
    ("v2.0.0", "1.99.99", Ordering::Greater),
    ("0.0.1", "0.1.0", Ordering::Less),
    ("1.2.9", "1.2.10", Ordering::Less),
    ("18446744073709551615.0.0", "1.0.0", Ordering::Greater),
];

const INVALID: [&str; 14] = [
    "",
    "1.2",
    "1.2.3.4",
    "01.2.3",
    "1.02.3",
    "1.2.-3",
    "1..3",
    " 1.2.3",
    "1.2.3 ",
    "V1.2.3",
    "vv1.2.3",
    "1.2.3-beta",
    "+1.2.3",
    "18446744073709551616.0.0",
];

#[test]
fn bench_hidden_compares_valid_versions() {
    for (left, right, expected) in ORDERED {
        assert_eq!(compare_versions(left, right), Some(expected), "{left} vs {right}");
    }
}

#[test]
fn bench_hidden_rejects_invalid_versions_on_either_side() {
    for version in INVALID {
        assert_eq!(compare_versions(version, "1.0.0"), None, "left {version:?}");
        assert_eq!(compare_versions("1.0.0", version), None, "right {version:?}");
    }
}
