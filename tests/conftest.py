from __future__ import annotations

import pytest

CSV_TEXT = (
    "order_id,region,amount,status\n"
    "1,East,100,shipped\n"
    "2,west,,pending\n"
    "2,west,,pending\n"  # exact duplicate of the previous row
    "3,East,50,shipped\n"
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Isolate the DuckDB file per test and never hit the real Claude API."""
    monkeypatch.setenv("OPSPILOT_DB_PATH", str(tmp_path / "test.duckdb"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield


@pytest.fixture
def orders_csv() -> bytes:
    return CSV_TEXT.encode("utf-8")
