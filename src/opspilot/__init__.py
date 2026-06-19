"""OpsPilot — deploy-in-a-day natural-language analytics over messy data.

Point it at a customer's CSV/Excel/Parquet exports; it loads them into DuckDB,
profiles schema + data health, and answers plain-English questions by generating
a safe, read-only SQL query (shown to the user for trust), running it on DuckDB,
and returning a table + chart. Works key-free as a SQL console + profiler;
natural-language answers light up when ANTHROPIC_API_KEY is set.
"""

__version__ = "0.1.0"
