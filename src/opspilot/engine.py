"""Query engine — ties safety, execution, and NL->SQL together.

``run_sql`` validates SELECT-only, enforces a row cap, runs on the read-only
connection, and returns JSON-safe columns/rows. ``ask`` builds schema context,
asks Claude, runs the SQL, and makes one repair attempt if the query errors.
"""

from __future__ import annotations

from typing import Any

from . import nl2sql
from .db import DBError, query_connection
from .profile import profile_all, schema_text
from .sqlsafe import UnsafeSQLError, enforce_limit, validate_select

ROW_CAP = 1000


def _json_safe(value: Any) -> Any:
    """Coerce a DuckDB cell into a JSON-serializable value."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def run_sql(sql: str) -> dict[str, Any]:
    """Validate, cap, and execute a read-only SQL query.

    Returns {columns, rows, sql, error}. On any failure ``error`` is populated
    and ``columns``/``rows`` are empty; nothing is ever mutated.
    """
    result: dict[str, Any] = {"columns": [], "rows": [], "sql": sql, "error": None}
    try:
        cleaned = validate_select(sql)
        capped = enforce_limit(cleaned, ROW_CAP)
        result["sql"] = capped
        with query_connection() as conn:
            cursor = conn.execute(capped)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchall()
        result["columns"] = columns
        result["rows"] = [[_json_safe(cell) for cell in row] for row in raw_rows]
    except (UnsafeSQLError, DBError) as exc:
        result["error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - execution errors surface to caller
        result["error"] = str(exc)
    return result


def ask(question: str) -> dict[str, Any]:
    """Answer a natural-language question via Claude-generated SQL.

    Returns {answer?, sql, columns, rows, error}. Without an API key, returns a
    graceful pointer to the SQL console. Makes one Claude repair attempt if the
    first generated query errors.
    """
    base: dict[str, Any] = {
        "answer": None,
        "sql": None,
        "columns": [],
        "rows": [],
        "error": None,
    }

    if not question or not question.strip():
        base["error"] = "Please enter a question."
        return base

    if not nl2sql.claude_enabled():
        base["error"] = (
            "Set ANTHROPIC_API_KEY for natural-language questions — "
            "or use the SQL console."
        )
        return base

    profiles = profile_all()
    if not profiles:
        base["error"] = "No data loaded. Upload a file first."
        return base

    schema = schema_text(profiles)

    try:
        sql = nl2sql.question_to_sql(schema, question)
    except nl2sql.NL2SQLError as exc:
        base["error"] = str(exc)
        return base

    outcome = run_sql(sql)
    base["sql"] = outcome["sql"]

    # One repair attempt if the generated query errored.
    if outcome["error"]:
        try:
            fixed = nl2sql.repair_sql(schema, question, sql, outcome["error"])
            outcome = run_sql(fixed)
            base["sql"] = outcome["sql"]
        except nl2sql.NL2SQLError as exc:
            base["error"] = str(exc)
            return base

    base["columns"] = outcome["columns"]
    base["rows"] = outcome["rows"]
    base["error"] = outcome["error"]
    if not outcome["error"]:
        base["answer"] = (
            f"Returned {len(outcome['rows'])} row(s)."
        )
    return base
