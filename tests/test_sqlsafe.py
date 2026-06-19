import pytest

from opspilot.sqlsafe import UnsafeSQLError, enforce_limit, has_limit, validate_select


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select region, count(*) from orders group by region",
        "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
        "SELECT created_at, order_date FROM orders",  # underscored cols != 'create'
        "SELECT 1; ",  # single trailing semicolon is allowed
    ],
)
def test_accepts_select(sql):
    assert validate_select(sql)  # returns cleaned sql, truthy


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "DROP TABLE orders",
        "INSERT INTO orders VALUES (1)",
        "UPDATE orders SET amount = 0",
        "ATTACH 'x.db'",
        "COPY orders TO 'out.csv'",
        "PRAGMA database_list",
        "SELECT 1; DROP TABLE orders",  # multi-statement
        "",
        "   ",
    ],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        validate_select(sql)


def test_strips_comments():
    cleaned = validate_select("SELECT 1 -- a comment\n/* block */")
    assert "comment" not in cleaned and "block" not in cleaned


def test_enforce_limit_adds_when_missing():
    out = enforce_limit("SELECT * FROM orders", cap=1000)
    assert "LIMIT 1000" in out and has_limit(out)


def test_enforce_limit_keeps_existing():
    sql = "SELECT * FROM orders LIMIT 5"
    assert enforce_limit(sql) == sql
