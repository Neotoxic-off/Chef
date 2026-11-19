Create a Python command-line tool in this folder that reads a TOML config file containing a list of endpoints (`[[endpoints]]` tables with `url` and `timeout` in seconds), validates it, and prints which entries are invalid and why.

Put the logic in a module `endpoints.py` at the folder root exposing `find_invalid(path: str) -> list[tuple[int, str]]`: the 0-based index and the reason of each invalid entry, in file order. An entry is valid when `url` is an http or https URL with a host, and `timeout` is a number (int or float, not a string or a boolean) greater than 0 and at most 300. A missing key makes the entry invalid.

Work autonomously: nobody will answer questions.
