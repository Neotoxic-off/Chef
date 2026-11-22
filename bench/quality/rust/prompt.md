Write a Rust 2024 library crate `ini` with `pub fn parse(input: &str) -> Result<Document, ParseError>`, where a document maps section names to ordered key-value pairs; keys before any section go in the section `""`. Lines are `[section]`, `key = value` or comments starting with `;` or `#`. `ParseError` carries the 1-based line number and what is wrong. A duplicate key in a section is an error.

Work autonomously: nobody will answer questions.
