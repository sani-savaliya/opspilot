import pytest

from opspilot.db import list_tables
from opspilot.ingest import IngestError, ingest_file, sanitize_table_name
from opspilot.profile import profile_all


def test_sanitize_table_name():
    assert sanitize_table_name("Orders 2024.csv") == "orders_2024"
    assert sanitize_table_name("123data.csv") == "t_123data"


def test_ingest_csv_creates_table(orders_csv):
    created = ingest_file("orders.csv", orders_csv)
    assert created == ["orders"]
    assert "orders" in list_tables()


def test_unsupported_type_raises():
    with pytest.raises(IngestError):
        ingest_file("notes.txt", b"hello")


def test_empty_file_raises():
    with pytest.raises(IngestError):
        ingest_file("orders.csv", b"")


def test_profile_detects_nulls_and_dupes(orders_csv):
    ingest_file("orders.csv", orders_csv)
    prof = profile_all()["orders"]
    assert prof["row_count"] == 4
    amount = next(c for c in prof["columns"] if c["name"] == "amount")
    assert amount["null_pct"] == 50.0
    assert prof["duplicate_rows"] == 1
    issue_types = {i["type"] for i in prof["issues"]}
    assert "high_null" in issue_types
    assert "duplicate_rows" in issue_types
