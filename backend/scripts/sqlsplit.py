"""Pure SQL statement splitter for the SynQ migration tool.

Splits a ``docs/db/schema.sql`` body into individual top-level SQL statements.
The obvious ``str.split(";")`` is not safe because the schema contains:

* single-quoted string literals with escaped quotes (``'it''s'``),
* ``$$ ... $$`` dollar-quoted PL/pgSQL function bodies that CONTAIN semicolons
  which must not be treated as statement terminators,
* tagged dollar-quotes (``$tag$ ... $tag$``),
* ``--`` line comments and ``/* ... */`` block comments.

This module is deliberately free of any asyncpg/argument-parsing imports so it
can be unit-tested in isolation.
"""

EMPTY = ""


def _delimiter_at(s: str, start: int) -> str | None:
    """Return the dollar-quote delimiter``(e.g. ``$$`` / ``$tag$``) opening at ``start``.

    The character at ``start`` must be ``$``. Valid tags (per PostgreSQL rules)
    are empty (``$$``) or a non-empty sequence that does not begin with a digit.
    Returns ``None`` when ``start`` is not the start of a valid dollar-quote
    (e.g. a bare ``$1`` parameter reference).
    """
    j = start + 1
    while j < len(s) and (s[j].isalnum() or s[j] == "_"):
        j += 1
    if j >= len(s) or s[j] != "$":
        return None
    tag = s[start + 1 : j]
    if tag and tag[0].isdigit():
        return None
    return s[start : j + 1]


def _find_balance(s: str, start: int) -> int:
    """Return the index just past a ``$tag$``/``$$`` object that opens at ``start``.

    The body runs to the FIRST occurrence of the identical delimiter. Returns
    ``len(s)`` when unterminated.
    """
    delimiter = _delimiter_at(s, start)
    if delimiter is None:
        return -1
    close = s.find(delimiter, start + len(delimiter))
    if close == -1:
        return len(s)
    return close + len(delimiter)


def split_statements(sql: str) -> list[str]:
    """Split ``sql`` into a list of executable top-level SQL statements.

    Handles single-quoted strings (with ``''`` escapes), ``$$``- and tagged
    ``$tag$`` dollar-quoted bodies, ``--`` line comments and ``/* ... */`` block
    comments. Empty/whitespace-only statements are dropped. Trailing semicolons
    are preserved so each element can be passed straight to ``asyncpg.execute``.
    """
    statements: list[str] = []
    current: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if ch == "'":
            # Single-quoted string; consume doubled quotes inside.
            current.append(ch)
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        current.append("''")
                        i += 2
                        continue
                    current.append("'")
                    i += 1
                    break
                current.append(sql[i])
                i += 1
            continue

        if ch == '"' and not (nxt == '"'):
            # Double-quoted identifier (case-sensitive names). Identifiers may
            # contain arbitrary chars except the literal ``"`` (escaped by ``""``).
            current.append(ch)
            i += 1
            while i < n:
                if sql[i] == '"':
                    if i + 1 < n and sql[i + 1] == '"':
                        current.append('""')
                        i += 2
                        continue
                    current.append('"')
                    i += 1
                    break
                current.append(sql[i])
                i += 1
            continue

        if ch == "$":
            # Tagged/plain dollar-quote: ``$tag$`` or ``$$``.
            idx = _find_balance(sql, i)
            if idx > i + 1:
                current.append(sql[i:idx])
                i = idx
                continue
            # Not a valid dollar-quote; treat the ``$`` as a plain character.
            current.append(ch)
            i += 1
            continue

        if ch == "-" and nxt == "-":
            # Line comment to end of line.
            j = sql.find("\n", i + 2)
            j = n if j == -1 else j
            current.append(sql[i:j])
            i = j
            continue

        if ch == "/" and nxt == "*":
            # Block comment to closing ``*/``.
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            current.append(sql[i:j])
            i = j
            continue

        if ch == ";":
            stmt = _strip(sql="".join(current))
            if stmt and not _is_comment_only(stmt):
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    tail = _strip(sql="".join(current))
    if tail and not _is_comment_only(tail):
        statements.append(tail)
    return statements


def _strip(sql: str) -> str:
    """Return ``sql`` stripped of leading/trailing whitespace."""
    return sql.strip()


def _is_comment_only(sql: str) -> bool:
    """Return True when ``sql`` contains only comments and whitespace."""
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "-" and nxt == "-":
            j = sql.find("\n", i + 2)
            i = n if j == -1 else j + 1
            continue
        if ch == "/" and nxt == "*":
            j = sql.find("*/", i + 2)
            if j == -1:
                return True
            i = j + 2
            continue
        # Any other non-whitespace, non-comment character makes it real SQL.
        return False
    return True
