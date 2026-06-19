from __future__ import annotations

import pytest

CSV_TEXT = (
    "order_id,region,amount,status\n"
    "1,East,100,shipped\n"
    "2,west,,pending\n"
    "2,west,,pending\n"  # exact duplicate of the previous row
    "3,East,50,shipped\n"
)


_LLM_KEYS = (
    "OPSPILOT_LLM_API_KEY", "OPSPILOT_LLM_PROVIDER", "OPSPILOT_LLM_MODEL",
    "OPSPILOT_LLM_BASE_URL", "NVIDIA_API_KEY", "NGC_API_KEY", "GROQ_API_KEY",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Isolate the DuckDB file per test and never hit any real LLM provider."""
    monkeypatch.setenv("OPSPILOT_DB_PATH", str(tmp_path / "test.duckdb"))
    for key in _LLM_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def orders_csv() -> bytes:
    return CSV_TEXT.encode("utf-8")
