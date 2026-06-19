"""Load uploaded files into DuckDB tables.

Supported types:
- ``.csv``     -> ``read_csv_auto``
- ``.parquet`` -> ``read_parquet``
- ``.xlsx``    -> pandas one-table-per-sheet, registered into DuckDB

Uploads are persisted to ``uploads/`` then loaded. Table names are sanitized
from filenames (and sheet names for Excel). Unsupported extensions raise
``IngestError``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .db import ingest_connection

UPLOAD_DIR = Path("uploads")
SUPPORTED_SUFFIXES = {".csv", ".parquet", ".xlsx"}


class IngestError(ValueError):
    """Raised when a file cannot be ingested (unsupported type, bad data)."""


def sanitize_table_name(raw: str) -> str:
    """Turn an arbitrary filename/sheet name into a safe SQL identifier.

    Lowercase, non-alphanumerics collapsed to underscores, leading digits
    prefixed with ``t_``. Empty results fall back to ``table``.
    """
    stem = Path(raw).stem if "." in raw else raw
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", stem).strip("_").lower()
    if not cleaned:
        cleaned = "table"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned


def _save_bytes(filename: str, data: bytes) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Use only the basename to avoid path traversal from the upload filename.
    safe_name = Path(filename).name
    dest = UPLOAD_DIR / safe_name
    dest.write_bytes(data)
    return dest


def ingest_file(filename: str, data: bytes) -> list[str]:
    """Persist ``data`` to uploads/ and load it into DuckDB.

    Returns the list of table names created. Raises IngestError on unsupported
    types or load failures.
    """
    if not filename:
        raise IngestError("Uploaded file has no name.")

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise IngestError(
            f"Unsupported file type '{suffix or filename}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}."
        )
    if not data:
        raise IngestError(f"Uploaded file '{filename}' is empty.")

    saved = _save_bytes(filename, data)

    try:
        if suffix == ".csv":
            return _ingest_csv(saved)
        if suffix == ".parquet":
            return _ingest_parquet(saved)
        return _ingest_xlsx(saved)
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface load errors clearly
        raise IngestError(f"Failed to load '{filename}': {exc}") from exc


def _ingest_csv(path: Path) -> list[str]:
    table = sanitize_table_name(path.name)
    with ingest_connection() as conn:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(
            f'CREATE TABLE "{table}" AS SELECT * FROM read_csv_auto(?)',
            [str(path)],
        )
    return [table]


def _ingest_parquet(path: Path) -> list[str]:
    table = sanitize_table_name(path.name)
    with ingest_connection() as conn:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(
            f'CREATE TABLE "{table}" AS SELECT * FROM read_parquet(?)',
            [str(path)],
        )
    return [table]


def _ingest_xlsx(path: Path) -> list[str]:
    sheets = pd.read_excel(path, sheet_name=None)  # dict[sheet_name -> DataFrame]
    if not sheets:
        raise IngestError(f"Workbook '{path.name}' contains no sheets.")

    base = sanitize_table_name(path.name)
    created: list[str] = []
    with ingest_connection() as conn:
        for sheet_name, frame in sheets.items():
            if len(sheets) == 1:
                table = base
            else:
                table = sanitize_table_name(f"{base}_{sheet_name}")
            # Register the DataFrame and materialize it as a persistent table.
            conn.register("_xlsx_frame", frame)
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.execute(
                f'CREATE TABLE "{table}" AS SELECT * FROM _xlsx_frame'
            )
            conn.unregister("_xlsx_frame")
            created.append(table)
    return created
