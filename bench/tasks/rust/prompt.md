Create a Rust command-line tool in this folder that takes two version numbers as arguments and prints `<`, `=` or `>` to say how the first compares with the second, or prints why a version is invalid and exits with code 1.

Make this folder a Cargo package named `versions` with a library, and expose from the library root `pub fn compare_versions(left: &str, right: &str) -> Option<std::cmp::Ordering>`, which returns `None` when either version is invalid. A valid version is `MAJOR.MINOR.PATCH`, optionally preceded by a single lowercase `v`: exactly three parts separated by dots, each written with digits only, without leading zeros (except `0` itself), and fitting in an unsigned 64-bit integer. Signs, whitespace, pre-release or build suffixes and any other character are invalid. Versions compare part by part, numerically (`1.10.0` is greater than `1.9.0`, `v1.2.3` equals `1.2.3`).

Work autonomously: nobody will answer questions.
