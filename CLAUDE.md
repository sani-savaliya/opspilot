# OpsPilot — project notes for Claude

Deploy-in-a-day natural-language analytics over messy customer data, on
DuckDB + Claude. Works key-free as a SQL console + profiler; NL→SQL lights up
with `ANTHROPIC_API_KEY`.

## Build & test

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
pytest                           # all tests must pass
opspilot                         # boots uvicorn on 127.0.0.1:8050
```

Boot check: `GET /api/status` → `{"tables": int, "claude_enabled": bool}`.

## Key files

- `src/opspilot/db.py` — read-write `ingest_connection`, **read-only** `query_connection`. The read-only connection is the core safety invariant; never weaken it.
- `src/opspilot/ingest.py` — CSV (`read_csv_auto`), Parquet (`read_parquet`), Excel (pandas per-sheet). `IngestError` on unsupported types. Table names sanitized from filenames.
- `src/opspilot/profile.py` — row count, per-column null_pct/distinct/3 samples, data-health (high-null >30%, constant, dup rows).
- `src/opspilot/sqlsafe.py` — `validate_select` (single SELECT/WITH, forbidden-keyword whole-word reject), `enforce_limit` (wrap + LIMIT 1000). `UnsafeSQLError` on violation. Defense-in-depth on top of read-only conn.
- `src/opspilot/nl2sql.py` — Anthropic SDK, model **`claude-opus-4-8`** (do NOT change; do NOT pass temperature/top_p/budget_tokens — they 400). Strips ```sql fences.
- `src/opspilot/engine.py` — `run_sql` (validate→cap→execute, JSON-safe rows), `ask` (schema→Claude→run, one repair attempt).
- `src/opspilot/app.py` — FastAPI: `/api/upload`, `/api/sources`, `/api/status`, `/api/query`, `/api/ask`, `/api/reset`, `/`.
- `src/opspilot/static/index.html` — single-file dark UI.

## Conventions

- Frozen-ish small typed files (<400 lines), explicit errors, validate inputs.
- Tests must never call the real Claude API — exercise the no-key paths.
- Env override `OPSPILOT_DB_PATH` isolates the DuckDB file (used by tests).

## Learnings

- DuckDB read-only connection requires the DB file to already exist; queries before any ingest raise a clear `DBError`.
