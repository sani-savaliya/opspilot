from pathlib import Path

from fastapi.testclient import TestClient

from opspilot.app import app

ORDERS = Path(__file__).resolve().parents[1] / "examples" / "orders.csv"


def _client() -> TestClient:
    return TestClient(app)


def test_status_and_sources_empty():
    c = _client()
    s = c.get("/api/status").json()
    assert s["tables"] == 0
    assert s["ai_enabled"] is False
    assert c.get("/api/sources").json()["tables"] == []


def test_upload_query_flow():
    c = _client()
    data = ORDERS.read_bytes()
    r = c.post("/api/upload", files={"files": ("orders.csv", data, "text/csv")})
    assert r.status_code == 200, r.text
    assert "orders" in r.json()["tables"]

    src = c.get("/api/sources").json()
    assert "orders" in src["tables"]
    assert "orders" in src["profiles"]

    q = c.post("/api/query", json={"sql": "SELECT count(*) AS n FROM orders"})
    assert q.status_code == 200
    assert q.json()["error"] is None
    assert q.json()["rows"][0][0] > 0


def test_query_blocks_mutation():
    c = _client()
    c.post("/api/upload", files={"files": ("orders.csv", ORDERS.read_bytes(), "text/csv")})
    out = c.post("/api/query", json={"sql": "DROP TABLE orders"}).json()
    assert out["error"] is not None


def test_ask_without_key():
    c = _client()
    c.post("/api/upload", files={"files": ("orders.csv", ORDERS.read_bytes(), "text/csv")})
    out = c.post("/api/ask", json={"question": "how many orders?"}).json()
    assert "OPSPILOT_LLM_API_KEY" in out["error"]


def test_unsupported_upload_rejected():
    c = _client()
    r = c.post("/api/upload", files={"files": ("notes.txt", b"hi", "text/plain")})
    assert r.status_code == 400


def test_home_serves_html():
    c = _client()
    r = c.get("/")
    assert r.status_code == 200
    assert "OpsPilot" in r.text
