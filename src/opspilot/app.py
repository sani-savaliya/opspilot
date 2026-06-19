"""FastAPI application for OpsPilot.

Endpoints:
- POST /api/upload   multipart files -> ingest -> {tables, profiles}
- GET  /api/sources  -> {tables, profiles, health, ai_enabled, provider}
- GET  /api/status   -> {tables, ai_enabled, provider}
- POST /api/query    {sql}      -> run_sql (key-free SQL console)
- POST /api/ask      {question} -> engine.ask (needs key)
- POST /api/reset    -> drop all tables / delete the duckdb file
- GET  /             -> static/index.html
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import db, engine
from .ingest import IngestError, ingest_file
from .nl2sql import llm_enabled, provider_label
from .profile import profile_all

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="OpsPilot",
    version="0.1.0",
    description="Natural-language analytics over messy data, on DuckDB + any LLM.",
)


class QueryRequest(BaseModel):
    sql: str


class AskRequest(BaseModel):
    question: str


def _health_from_profiles(profiles: dict) -> list[dict]:
    """Flatten per-table issues into a single health list for the UI."""
    health: list[dict] = []
    for table, prof in profiles.items():
        for issue in prof.get("issues", []):
            health.append({"table": table, **issue})
    return health


@app.get("/api/status")
def status() -> dict:
    return {
        "tables": len(db.list_tables()),
        "ai_enabled": llm_enabled(),
        "provider": provider_label(),
    }


@app.get("/api/sources")
def sources() -> dict:
    profiles = profile_all()
    return {
        "tables": db.list_tables(),
        "profiles": profiles,
        "health": _health_from_profiles(profiles),
        "ai_enabled": llm_enabled(),
        "provider": provider_label(),
    }


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)) -> JSONResponse:
    if not files:
        return JSONResponse(
            status_code=400, content={"error": "No files uploaded."}
        )
    created: list[str] = []
    errors: list[str] = []
    for upload_file in files:
        try:
            data = await upload_file.read()
            created.extend(ingest_file(upload_file.filename or "", data))
        except IngestError as exc:
            errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001 - report, don't crash the request
            errors.append(f"{upload_file.filename}: {exc}")

    if not created and errors:
        return JSONResponse(status_code=400, content={"error": "; ".join(errors)})

    profiles = profile_all()
    return JSONResponse(
        content={
            "tables": created,
            "profiles": profiles,
            "health": _health_from_profiles(profiles),
            "errors": errors,
        }
    )


@app.post("/api/query")
def query(req: QueryRequest) -> dict:
    return engine.run_sql(req.sql)


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    return engine.ask(req.question)


@app.post("/api/reset")
def reset() -> dict:
    db.reset()
    return {"tables": 0, "ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
