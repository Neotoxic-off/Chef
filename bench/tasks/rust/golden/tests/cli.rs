use std::process::{Command, Output};

fn run(arguments: &[&str]) -> Result<Output, std::io::Error> {
    Command::new(env!("CARGO_BIN_EXE_versions"))
        .args(arguments)
        .output()
}

#[test]
fn prints_greater_than() -> Result<(), std::io::Error> {
    let output = run(&["1.10.0", "1.9.0"])?;
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim_end(), ">");
    assert_eq!(output.status.code(), Some(0));
    Ok(())
}

#[test]
fn prints_less_than() -> Result<(), std::io::Error> {
    let output = run(&["1.2.3", "1.2.4"])?;
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim_end(), "<");
    Ok(())
}

#[test]
fn prints_equal_ignoring_v_prefix() -> Result<(), std::io::Error> {
    let output = run(&["v1.2.3", "1.2.3"])?;
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim_end(), "=");
    Ok(())
}

#[test]
fn invalid_version_explains_and_exits_with_one() -> Result<(), std::io::Error> {
    let output = run(&["1.2.3", "1.02.3"])?;
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(output.stdout, Vec::<u8>::new());
    assert_eq!(
        String::from_utf8_lossy(&output.stderr).trim_end(),
        "invalid right version \"1.02.3\": part 2 has a leading zero"
    );
    Ok(())
}

#[test]
fn wrong_argument_count_prints_usage_and_exits_with_two() -> Result<(), std::io::Error> {
    let output = run(&["1.2.3"])?;
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8_lossy(&output.stderr).trim_end(),
        "usage: versions <left> <right>"
    );
    Ok(())
}
