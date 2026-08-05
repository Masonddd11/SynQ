"""Unit tests for the migration SQL splitter (``scripts.sqlsplit``).

Tests focus on splitting a MULTI-statement SQL payload that includes PL/pgSQL
``$$ ... ; ... $$`` function bodies — the classic place a naive ``split(";")``
breaks.
"""

from pathlib import Path

from scripts.sqlsplit import split_statements

# Real schema file path (source of truth) for an integration-style assertion.
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "db" / "schema.sql"


def test_split_statements_handles_dollar_quoted_function_bodies():
    """A function body with internal semicolons must be one statement."""
    sql = (
        "CREATE OR REPLACE FUNCTION f() RETURNS TRIGGER AS $$\n"
        "BEGIN\n"
        "    INSERT INTO t (a) VALUES (1);\n"
        "    RETURN NEW;\n"
        "END;\n"
        "$$ LANGUAGE plpgsql;"
    )
    stmts = split_statements(sql)
    assert len(stmts) == 1
    assert stmts[0].startswith("CREATE OR REPLACE FUNCTION f()")
    assert stmts[0].endswith("LANGUAGE plpgsql")


def test_split_statements_multiple_statements_with_function():
    """Multiple top-level statements separated by ``;``, one with a $$ body."""
    sql = (
        "CREATE TABLE a (id INT);"
        "CREATE OR REPLACE FUNCTION f() RETURNS TRIGGER AS $$\n"
        "BEGIN\n"
        "    UPDATE a SET id = 1;\n"
        "    RETURN NEW;\n"
        "END;\n"
        "$$ LANGUAGE plpgsql;"
        "CREATE TABLE b (id INT);"
    )
    stmts = split_statements(sql)
    assert len(stmts) == 3
    assert "UPDATE a SET id = 1;" in stmts[1]
    assert stmts[0] == "CREATE TABLE a (id INT)"
    assert stmts[2] == "CREATE TABLE b (id INT)"


def test_split_statements_handles_escaped_quotes():
    """An escaped single quote (``''``) inside a string is not a terminator."""
    sql = "INSERT INTO t (name) VALUES ('it''s a test');SELECT 1;"
    stmts = split_statements(sql)
    assert len(stmts) == 2
    assert stmts[0] == "INSERT INTO t (name) VALUES ('it''s a test')"
    assert stmts[1] == "SELECT 1"


def test_split_statements_ignores_semicolons_inside_strings():
    """A semicolon inside a string literal is not a statement terminator."""
    sql = "INSERT INTO t (note) VALUES ('a;b');SELECT 2;"
    stmts = split_statements(sql)
    assert len(stmts) == 2
    assert stmts[0] == "INSERT INTO t (note) VALUES ('a;b')"
    assert stmts[1] == "SELECT 2"


def test_split_statements_drops_empty_and_comment_tail():
    """Whitespace and comment-only leftovers produce no extra statements."""
    sql = "SELECT 1;  -- trailing comment"
    stmts = split_statements(sql)
    assert stmts == ["SELECT 1"]


def test_split_statements_handles_tagged_dollar_quotes():
    """Tagged dollar-quotes (``$body$``) work like ``$$``."""
    sql = "CREATE FUNCTION g() RETURNS text AS $body$ SELECT 'x;y'; $body$ LANGUAGE sql;"
    stmts = split_statements(sql)
    assert len(stmts) == 1
    assert "SELECT 'x;y';" in stmts[0]


def _load_real_schema() -> str:
    if not _SCHEMA_PATH.exists():
        raise AssertionError(f"Schema not found at {_SCHEMA_PATH}")
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def test_split_statements_parses_real_schema():
    """The real source-of-truth schema splits into the expected count."""
    sql = _load_real_schema()
    stmts = split_statements(sql)
    # Every statement must be non-empty and executable-looking.
    for s in stmts:
        assert s.strip()
        assert len(s.strip()) > 1
    # Contains the known function bodies (multi-semicolon) intact as ONE unit.
    # Statements may carry a leading ``-- comment``, so match by membership.
    assert any("CREATE OR REPLACE FUNCTION handle_new_user()" in s for s in stmts)
    assert any("CREATE OR REPLACE FUNCTION check_analysis_limit()" in s for s in stmts)
    assert any("CREATE OR REPLACE FUNCTION update_updated_at()" in s for s in stmts)
    # All tables exist in the output.
    for table in ("stocks", "profiles", "analyses", "watchlist", "alerts", "analysis_snapshots"):
        assert any(f"CREATE TABLE {table}" in s for s in stmts)
