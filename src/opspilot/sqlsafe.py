"""Read-only SQL validation — defense-in-depth on top of the read-only connection.

``validate_select`` strips comments, rejects multi-statement input, requires a
single SELECT/WITH statement, and bans any forbidden keyword appearing as a
whole word. ``enforce_limit`` wraps the query in a bounded subquery when it has
no LIMIT of its own.
"""

from __future__ import annotations

import re

# Keywords that can mutate, exfiltrate, or escape the sandbox. Matched as whole
# words (case-insensitive), so a column named "update_date" stays safe but a
# bare UPDATE is rejected.
FORBIDDEN_KEYWORDS = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "attach",
        "detach",
        "copy",
        "pragma",
        "install",
        "load",
        "export",
        "set",
        "call",
        "replace",
        "truncate",
        "merge",
        "grant",
        "revoke",
    }
)


class UnsafeSQLError(ValueError):
    """Raised when SQL is not a safe, single, read-only SELECT statement."""


def _strip_comments(sql: str) -> str:
    """Remove -- line comments and /* */ block comments."""
    # Block comments (non-greedy, across newlines).
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Line comments to end of line.
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def validate_select(sql: str) -> str:
    """Validate that ``sql`` is a single read-only SELECT/WITH statement.

    Returns the cleaned SQL (comments stripped, trailing semicolon removed).
    Raises UnsafeSQLError on any violation.
    """
    if sql is None or not sql.strip():
        raise UnsafeSQLError("Empty query.")

    cleaned = _strip_comments(sql).strip()
    # Drop a single trailing semicolon; anything else multi-statement is caught.
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    if not cleaned:
        raise UnsafeSQLError("Query is empty after removing comments.")

    # Reject multiple statements (a semicolon remaining inside the body).
    if ";" in cleaned:
        raise UnsafeSQLError("Only a single statement is allowed.")

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise UnsafeSQLError("Only SELECT or WITH queries are allowed.")

    # Whole-word forbidden keyword check.
    words = set(re.findall(r"[a-z_]+", lowered))
    hits = sorted(words & FORBIDDEN_KEYWORDS)
    if hits:
        raise UnsafeSQLError(
            f"Query contains forbidden keyword(s): {', '.join(hits)}."
        )

    return cleaned


def has_limit(sql: str) -> bool:
    """True if the query already has a top-level LIMIT clause (heuristic)."""
    return re.search(r"\blimit\b", sql, flags=re.IGNORECASE) is not None


def enforce_limit(sql: str, cap: int = 1000) -> str:
    """Wrap ``sql`` so at most ``cap`` rows are returned when no LIMIT is present."""
    if cap <= 0:
        raise UnsafeSQLError("Row cap must be a positive integer.")
    if has_limit(sql):
        return sql
    return f"SELECT * FROM ({sql}) AS _q LIMIT {cap}"
