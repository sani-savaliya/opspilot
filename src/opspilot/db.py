"""DuckDB access layer.

Two connection paths enforce the core safety invariant:
- ``ingest_connection`` is read-write and used only by the loader.
- ``query_connection`` is ``read_only=True`` — queries can NEVER mutate the
  database, no matter what SQL slips past the validator. This is the bedrock of
  OpsPilot's trust model; the SELECT-only validator is defense-in-depth on top.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

# Persistent on-disk database. Configurable via env so tests can isolate.
DEFAULT_DB_PATH = Path("data") / "opspilot.duckdb"


class DBError(RuntimeError):
    """Raised when a DuckDB operation cannot be completed."""


def db_path() -> Path:
    """Resolve the active database path (env override wins)."""
    override = os.environ.get("OPSPILOT_DB_PATH")
    path = Path(override) if override else DEFAULT_DB_PATH
    return path


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def ingest_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """Read-write connection for loading data. Always closed on exit."""
    path = db_path()
    _ensure_parent(path)
    conn = duckdb.connect(str(path))
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def query_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """Read-only connection for queries. Mutations are impossible here.

    Raises DBError if the database file does not exist yet (nothing ingested).
    """
    path = db_path()
    if not path.exists():
        raise DBError(
            "No data has been loaded yet. Upload a CSV, Excel, or Parquet file first."
        )
    conn = duckdb.connect(str(path), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def list_tables() -> list[str]:
    """Return the names of all base tables, sorted. Empty list if no DB yet."""
    path = db_path()
    if not path.exists():
        return []
    conn = duckdb.connect(str(path), read_only=True)
    try:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def reset() -> None:
    """Drop everything by deleting the database file (and its WAL)."""
    path = db_path()
    for candidate in (path, path.with_suffix(path.suffix + ".wal")):
        try:
            if candidate.exists():
                candidate.unlink()
        except OSError as exc:  # pragma: no cover - filesystem edge
            raise DBError(f"Could not reset database: {exc}") from exc
