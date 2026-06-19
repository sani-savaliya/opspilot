"""Schema + data-health profiling for loaded tables.

For each table this computes (via DuckDB SQL):
- row count
- per-column {name, type, null_pct, distinct_count, sample (3 values)}
- a data-health issue list:
    * columns with null_pct > 30%
    * constant columns (distinct_count <= 1 over non-empty tables)
    * exact duplicate row count

All values are returned as plain JSON-safe dicts.
"""

from __future__ import annotations

from typing import Any

from .db import list_tables, query_connection

HIGH_NULL_THRESHOLD = 30.0  # percent


def _safe(value: Any) -> Any:
    """Coerce DuckDB values into JSON-serializable forms."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def profile_table(conn, table: str) -> dict[str, Any]:
    """Profile a single table using an existing read-only connection."""
    row_count = conn.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]

    col_rows = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'main' AND table_name = ? ORDER BY ordinal_position",
        [table],
    ).fetchall()

    columns: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for name, dtype in col_rows:
        quoted = f'"{name}"'
        if row_count > 0:
            null_count, distinct_count = conn.execute(
                f'SELECT COUNT(*) FILTER (WHERE {quoted} IS NULL), '
                f'COUNT(DISTINCT {quoted}) FROM "{table}"'
            ).fetchone()
            null_pct = round(100.0 * null_count / row_count, 2)
        else:
            null_count = 0
            distinct_count = 0
            null_pct = 0.0

        samples = conn.execute(
            f'SELECT DISTINCT {quoted} FROM "{table}" '
            f'WHERE {quoted} IS NOT NULL LIMIT 3'
        ).fetchall()
        sample_values = [_safe(s[0]) for s in samples]

        columns.append(
            {
                "name": name,
                "type": str(dtype),
                "null_pct": null_pct,
                "distinct_count": int(distinct_count),
                "sample": sample_values,
            }
        )

        if row_count > 0 and null_pct > HIGH_NULL_THRESHOLD:
            issues.append(
                {
                    "type": "high_null",
                    "column": name,
                    "detail": f"{null_pct:.0f}% null",
                }
            )
        if row_count > 0 and distinct_count <= 1:
            issues.append(
                {
                    "type": "constant_column",
                    "column": name,
                    "detail": "constant column",
                }
            )

    duplicate_rows = 0
    if row_count > 0 and col_rows:
        col_list = ", ".join(f'"{c[0]}"' for c in col_rows)
        # Count rows beyond the first occurrence of each distinct row.
        duplicate_rows = conn.execute(
            f"SELECT COALESCE(SUM(cnt - 1), 0) FROM "
            f"(SELECT COUNT(*) AS cnt FROM \"{table}\" "
            f"GROUP BY {col_list} HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        duplicate_rows = int(duplicate_rows)
        if duplicate_rows > 0:
            issues.append(
                {
                    "type": "duplicate_rows",
                    "column": None,
                    "detail": f"{duplicate_rows} dupes",
                }
            )

    return {
        "table": table,
        "row_count": int(row_count),
        "columns": columns,
        "duplicate_rows": duplicate_rows,
        "issues": issues,
    }


def profile_all() -> dict[str, dict[str, Any]]:
    """Profile every loaded table. Returns {table_name: profile}."""
    tables = list_tables()
    if not tables:
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    with query_connection() as conn:
        for table in tables:
            profiles[table] = profile_table(conn, table)
    return profiles


def schema_text(profiles: dict[str, dict[str, Any]]) -> str:
    """Render a compact schema description for the LLM prompt."""
    lines: list[str] = []
    for table, prof in profiles.items():
        lines.append(f'Table "{table}" ({prof["row_count"]} rows):')
        for col in prof["columns"]:
            samples = ", ".join(str(s) for s in col["sample"][:3])
            lines.append(
                f'  - "{col["name"]}" {col["type"]} '
                f'(nulls {col["null_pct"]}%, samples: {samples})'
            )
    return "\n".join(lines)
