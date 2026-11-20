use std::cmp::Ordering;
use std::process::ExitCode;

use versions::{Version, VersionError, parse_version};

const INVALID_VERSION_EXIT: u8 = 1;
const USAGE_EXIT: u8 = 2;

fn parse_argument(name: &str, text: &str) -> Result<Version, String> {
    parse_version(text)
        .map_err(|error: VersionError| format!("invalid {name} version {text:?}: {error}"))
}

fn symbol(ordering: Ordering) -> char {
    match ordering {
        Ordering::Less => '<',
        Ordering::Equal => '=',
        Ordering::Greater => '>',
    }
}

fn run(arguments: &[String]) -> Result<char, String> {
    let [left, right] = arguments else {
        return Err("usage: versions <left> <right>".to_owned());
    };
    let left = parse_argument("left", left)?;
    let right = parse_argument("right", right)?;
    Ok(symbol(left.cmp(&right)))
}

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    match run(&arguments) {
        Ok(symbol) => {
            println!("{symbol}");
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("{message}");
            let usage = arguments.len() != 2;
            ExitCode::from(if usage {
                USAGE_EXIT
            } else {
                INVALID_VERSION_EXIT
            })
        }
    }
}
