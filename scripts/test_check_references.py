from pathlib import Path

import check_references

VERSION_LINE = "Written for Thing 1.0 (Nov 2026), not benchmarked."


def write_reference(directory: Path, name: str, body: str, version_line: str = VERSION_LINE) -> None:
    (directory / name).write_text(f"# Title\n\n{version_line}\n\n{body}", encoding="utf-8")


def test_the_repository_references_pass() -> None:
    report = check_references.check_references(check_references.REFERENCES_DIR)
    check_references.check_images(report, check_references.read_images(check_references.IMAGES_FILE))
    assert report.errors == []
    assert report.version_lines >= 100
    assert report.parsed["yaml"] > 0


def test_valid_blocks_and_links_pass_and_unknown_languages_are_counted(tmp_path: Path) -> None:
    write_reference(tmp_path, "other.md", "")
    body = (
        "See `other.md`.\n\n```yaml\na: [1, 2]\n---\nb: !Ref x\n```\n\n"
        "```json\nPUT _index/x\n{}\n```\n\n```python\n%autoreload 2\nx = 1\n```\n\n"
        "- item:\n  ```toml\n  [tool]\n  x = 1\n  ```\n\n```rust\nfn main() {}\n```\n\n```\nplain\n```\n"
    )
    write_reference(tmp_path, "good.md", body, "Verified against Thing 2.0 (Nov 2026).")

    report = check_references.check_references(tmp_path)

    assert report.errors == []
    assert report.links == 1
    assert report.parsed == {"yaml": 1, "json": 1, "python": 1, "toml": 1}
    assert report.skipped == {"rust": 1, "(none)": 1}


def test_docker_run_yields_the_image_after_its_options_only(tmp_path: Path) -> None:
    body = (
        'Lint, like python:3.13: `MSYS_NO_PATHCONV=1; src=$(cygpath -m "$PWD"); docker run --rm -v "$src:/w" --user "$(id -u):$(id -g)" '
        'ghcr.io/org/tool:v1.2.3 sh -c "npm run lint:fix"`\n'
        "Build: `docker run --rm -p 8080:8080 -i hadolint/hadolint:<tag> - < Dockerfile && docker run --init gcc:15 make`\n"
        "Pinned: `docker run --platform=linux/amd64 localhost:5000/tool:1 && docker run tool@sha256:ab12`\n"
    )
    write_reference(tmp_path, "tools.md", body)

    report = check_references.check_references(tmp_path)

    assert report.errors == []
    assert report.images == {"ghcr.io/org/tool:v1.2.3", "gcc:15", "localhost:5000/tool:1", "tool@sha256:ab12"}


def test_a_braced_pwd_mount_fails(tmp_path: Path) -> None:
    write_reference(tmp_path, "tools.md", 'Run `MSYS_NO_PATHCONV=1 docker run --rm -v "${PWD}:/w" tool/tool:1 .`\n')

    errors = check_references.check_references(tmp_path).errors

    assert errors == ["tools.md:5: mounts $PWD, which Git Bash can map to an empty folder; mount $src"]


def test_a_src_mount_without_cygpath_or_path_conversion_off_fails(tmp_path: Path) -> None:
    write_reference(tmp_path, "tools.md", 'Run `src=$PWD; docker run --rm --mount "type=bind,src=$src,dst=/w" tool/tool:1 .`\n')

    errors = check_references.check_references(tmp_path).errors

    assert errors == [
        "tools.md:5: mounts $src without MSYS_NO_PATHCONV=1",
        'tools.md:5: mounts $src without src=$(cygpath -m "$PWD")',
    ]


def test_an_untagged_image_and_an_unbalanced_quote_fail(tmp_path: Path) -> None:
    write_reference(tmp_path, "tools.md", "Run `docker run --rm tool/tool .` or `docker run -e 'A=1 tool:1`\n")

    errors = check_references.check_references(tmp_path).errors

    assert errors == [
        "tools.md:5: runs image tool/tool without a tag",
        "tools.md:5: cannot split the docker run command: No closing quotation",
    ]


def test_unlisted_and_unused_images_fail() -> None:
    report = check_references.Report(images={"run/only:1", "both:2"})

    check_references.check_images(report, {"both:2", "listed/only:3"})

    assert report.errors == [
        "image run/only:1 is run by a reference but not listed in container-images.txt",
        "image listed/only:3 is listed in container-images.txt but no reference runs it",
    ]


def test_read_images_skips_blank_lines(tmp_path: Path) -> None:
    images_file = tmp_path / "images.txt"
    images_file.write_text("a/b:1\n\n  c:2  \n", encoding="utf-8")

    assert check_references.read_images(images_file) == {"a/b:1", "c:2"}


def test_a_broken_link_an_invalid_yaml_block_and_a_missing_version_line_fail(tmp_path: Path) -> None:
    write_reference(tmp_path, "bad.md", "See `missing.md`.\n\n```yaml\na: {b: ${c}:1}\n```\n", "Some prose.")

    errors = check_references.check_references(tmp_path).errors

    assert len(errors) == 3
    assert errors[0].startswith("bad.md:3: no version line")
    assert errors[1] == "bad.md: mentions missing.md, which is not a reference"
    assert errors[2].startswith("bad.md:7: yaml block does not parse")
