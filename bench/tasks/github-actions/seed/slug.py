import re

NON_ALPHANUMERIC: re.Pattern[str] = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    return NON_ALPHANUMERIC.sub("-", title.lower()).strip("-")
