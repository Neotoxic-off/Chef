from slug import slugify


def test_slugify_joins_words_with_hyphens() -> None:
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_of_empty_title_is_empty() -> None:
    assert slugify("") == ""
