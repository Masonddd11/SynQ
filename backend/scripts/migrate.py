"""Apply the SynQ schema (``docs/db/schema.sql``) to a PostgreSQL database.

Standalone, idempotent, asyncpg-based schema applier. Reads the source-of-truth
schema file, splits it into individual statements (see ``sqlsplit``), executes
each one against the target database, then verifies the resulting ``public``
tables.

Usage::

    python -m scripts.migrate [--dsn DSN] [--dry-run] [--yes] [--ssl]

Safety:

* The target host/database is always printed before any DDL, and the user is
  prompted for confirmation unless ``--yes`` is passed.
* ``--dry-run`` prints the statements that WOULD run and never prompts or
  executes anything.
* The default ``settings.database_url`` (local docker-compose ``localhost``)
  is reported clearly as a non-remote target.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings
from scripts.sqlsplit import split_statements

# Path to the source-of-truth schema relative to the backend repo root.
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "db" / "schema.sql"

_LOCAL_DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/synq"

# asyncpg duplicate-object error codes: unique_violation (23505) and duplicate
# various are wrapped in these Postgres error classes we may safely ignore when
# re-applying an idempotent schema.
_DUPLICATE_CODES = {
    "23505",  # unique_violation
    "42710",  # duplicate_object (table/function/trigger already exists)
    "42P07",  # duplicate_table
}
# PostgreSQL error codes that indicate the target already has the object.
_IDEMPOTENT_OK_CODES = _DUPLICATE_CODES


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.migrate",
        description="Idempotently apply the SynQ PostgreSQL schema.",
    )
    parser.add_argument("--dsn", default=None, help="Full PostgreSQL DSN to target.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print statements without executing.",
    )
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    parser.add_argument(
        "--ssl",
        default=None,
        help=(
            "SSL mode. Set to 'require' for Supabase. "
            "Auto-detected from DSN query param if absent."
        ),
    )
    return parser.parse_args(argv)


def _resolve_dsn(argv: list[str] | None = None) -> argparse.Namespace:
    """Fill ``args.dsn`` from the CLI flag or fall back to ``settings.database_url``."""
    args = _parse_args(argv)
    if args.dsn is None:
        args.dsn = settings.database_url
    return args


def _dsn_host(dsn: str) -> str:
    """Return just the host portion of a DSN for display."""
    parsed = urlparse(dsn)
    return f"{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")


def _dsn_ssl(dsn: str) -> bool:
    """Detect an ``sslmode=require`` query param on the DSN."""
    parsed = urlparse(dsn)
    query = parsed.query.lower()
    return "sslmode=require" in query


def _read_schema() -> str:
    """Read the schema file from the repo, erroring if it is missing."""
    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found at {_SCHEMA_PATH}")
    return _SCHEMA_PATH.read_text(encoding="utf-8")


async def _apply(conn, statements: list[str]) -> None:
    """Execute each statement, treating duplicate-object errors as OK."""
    for stmt in statements:
        try:
            await conn.execute(stmt)
        except Exception as exc:  # noqa: BLE001 - map asyncpg errors generically
            if _is_duplicate_error(exc):
                _first = _statement_name(stmt)
                print(f"  [SKIP] already exists: {_first}")
            else:
                raise


def _is_duplicate_error(exc: Exception) -> bool:
    """Return True when the exception is a PostgreSQL duplicate-object error."""
    code = getattr(exc, "sqlstate", None) or getattr(exc, "pgerror", None)
    if isinstance(code, str) and code in _IDEMPOTENT_OK_CODES:
        return True
    # Fallback: asyncpg stores the SQLSTATE in ``sqlstate``; some errors embed it
    # in the ``pgerror`` string like ``SQLSTATE 42P07``.
    message = str(getattr(exc, "pgerror", "") or str(exc))
    return any(state in message for state in _IDEMPOTENT_OK_CODES)


def _statement_name(stmt: str) -> str:
    """Return a short name for a statement for logging."""
    body = _strip_leading_comments(stmt)
    first = re.split(r"\s+", body.strip(), maxsplit=1)[0].upper()
    rest = body.strip()[len(first) :].lstrip()
    if first in {"CREATE", "ALTER"}:
        second = re.split(r"\s+", rest, maxsplit=1)[0].upper()
        return f"{first} {second}".strip() or first
    return first or "(?)"


def _strip_leading_comments(sql: str) -> str:
    """Remove comment lines/blocks from the start of ``sql``."""
    body = sql.lstrip(" \t\r\n")
    stripped = True
    while stripped:
        stripped = False
        if body.startswith("--"):
            nl = body.find("\n")
            if nl == -1:
                return ""
            body = body[nl + 1 :].lstrip(" \t\r\n")
            stripped = True
        elif body.startswith("/*"):
            end = body.find("*/")
            body = "" if end == -1 else body[end + 2 :].lstrip(" \t\r\n")
            stripped = True
    return body


async def _verify_tables(conn) -> list[str]:
    """Return the sorted list of user tables in the ``public`` schema."""
    rows = await conn.fetch(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    )
    return [row["tablename"] for row in rows]


async def _confirm(host: str, dry_run: bool, yes: bool) -> bool:
    """Return True when the user confirms applying DDL to ``host``."""
    if dry_run:
        return False
    if yes:
        return True
    answer = input(f"Apply schema to {host}? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


async def _run_apply(args: argparse.Namespace, statements: list[str]) -> int:
    """Execute statements against the target DSN and verify the tables."""
    dsn = args.dsn
    ssl_mode = args.ssl if args.ssl is not None else ("require" if _dsn_ssl(dsn) else None)
    host = _dsn_host(dsn)

    print(f"Target: {host}")
    print(f"Statements to apply: {len(statements)}")
    if _is_local(dsn):
        print("NOTE: target is the LOCAL docker-compose default (localhost).")

    if not await _confirm(host, args.dry_run, args.yes):
        if not args.dry_run:
            print("Aborted; no changes applied.")
        return 1 if not args.dry_run else 0

    import asyncpg

    conn = await asyncpg.connect(dsn=dsn, ssl=ssl_mode)
    try:
        await _apply(conn, statements)
        tables = await _verify_tables(conn)
        print(f"\nVerification: {len(tables)} tables present in 'public':")
        for t in tables:
            print(f"  - {t}")
    finally:
        await conn.close()
    return 0


def _is_local(dsn: str) -> bool:
    """Return True when the DSN targets the localhost docker default."""
    parsed = urlparse(dsn)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


async def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    args = _resolve_dsn(argv)
    schema = _read_schema()
    statements = split_statements(schema)
    print(f"Parsed {len(statements)} statements from {_SCHEMA_PATH.name}.")

    if args.dry_run:
        print("\n--dry-run: would execute the following statements --")
        for stmt in statements:
            print(f"  · {_statement_name(stmt)}")
        print("\nExpected public tables:")
        for t in _expected_tables(statements):
            print(f"  - {t}")
        return 0

    if _is_local(args.dsn):
        # Loud, explicit note: the local docker DB is NOT a safe default target.
        print("WARNING: applying to the local docker-compose database (localhost).")
        print("         This is the fallback default; use --dsn to target a real DB.")

    return await _run_apply(args, statements)


def _expected_tables(statements: list[str]) -> list[str]:
    """Best-effort list of tables we expect to exist after applying the schema."""
    tables: set[str] = set()
    for stmt in statements:
        body = _strip_leading_comments(stmt)
        # Match an unqualified "CREATE TABLE <name> ..."
        m = re.match(
            r"\s*CREATE\s+(?:UNLOGGED\s+|TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)",
            body,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            tables.add(m.group(1))
    return sorted(tables)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
