from opspilot.engine import ask, run_sql
from opspilot.ingest import ingest_file


def test_run_sql_returns_rows(orders_csv):
    ingest_file("orders.csv", orders_csv)
    out = run_sql("SELECT count(*) AS n FROM orders")
    assert out["error"] is None
    assert out["columns"] == ["n"]
    assert out["rows"] == [[4]]


def test_run_sql_groupby(orders_csv):
    ingest_file("orders.csv", orders_csv)
    out = run_sql("SELECT region, count(*) AS c FROM orders GROUP BY region ORDER BY c DESC")
    assert out["error"] is None
    assert any(row[0] == "East" for row in out["rows"])


def test_mutating_query_is_blocked(orders_csv):
    ingest_file("orders.csv", orders_csv)
    out = run_sql("DELETE FROM orders")
    assert out["error"] is not None
    # table untouched — still 4 rows
    assert run_sql("SELECT count(*) FROM orders")["rows"] == [[4]]


def test_ask_without_key_is_graceful(orders_csv):
    ingest_file("orders.csv", orders_csv)
    out = ask("how many orders are there?")
    assert out["sql"] is None
    assert "ANTHROPIC_API_KEY" in out["error"]
