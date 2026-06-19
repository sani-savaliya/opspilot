# OpsPilot

**Deploy-in-a-day natural-language analytics over a customer's messy data.**

A Forward-Deployed-Engineer flagship. Point it at a customer's exports — CSV,
Excel, Parquet — and OpsPilot auto-loads them into DuckDB, profiles the schema
and data health, and lets non-technical ops users ask questions in plain
English. An LLM generates a **safe, read-only** SQL query, OpsPilot runs it on
DuckDB, and returns the answer as a table + chart — **always showing the
generated SQL, so the user can trust and verify it.**

It works **key-free** as a SQL console + data profiler. Natural-language answers
light up with **any OpenAI-compatible provider** — NVIDIA NIM, Groq, Google
Gemini, OpenRouter, or OpenAI (all have free tiers).

---

## The engagement (why this exists)

Ops teams sit on piles of messy exports — a daily orders dump, a customer list,
a finance spreadsheet with three sheets. The people who need answers ("which
region slipped last month?") are not the people who can write SQL. A forward-
deployed engineer's job is to stand up a working solution against *that
customer's actual data*, fast, without a six-week data-warehouse project.

OpsPilot is that solution in a box:

1. **Drop the files in.** It infers schema and types automatically (DuckDB's
   `read_csv_auto` / `read_parquet`, pandas for Excel sheets).
2. **See what you're working with.** Per-column null rates, distinct counts,
   sample values, plus a data-health readout (high-null columns, constant
   columns, duplicate rows) so nobody trusts dirty data blindly.
3. **Ask in English.** Claude turns the question into one DuckDB `SELECT`.
4. **Trust it.** The generated SQL is shown in an editable box — it doubles as a
   SQL console with a **Run SQL** button.

---

## Trust & safety model

OpsPilot never lets a question mutate the customer's data. Two independent
layers enforce this:

- **Read-only connection.** Queries run on `duckdb.connect(path, read_only=True)`.
  Even a malicious query physically cannot write.
- **SELECT-only validation** (`sqlsafe.py`). Before execution, every query is
  stripped of comments, rejected if it is not a single statement, required to
  start with `SELECT`/`WITH`, and rejected if it contains any forbidden keyword
  (`insert`, `update`, `delete`, `drop`, `alter`, `create`, `attach`, `copy`,
  `pragma`, `install`, `load`, …) as a whole word. A row cap is enforced.
- **The SQL is shown.** No black box — the user sees and can edit the exact
  query that produced the answer.

---

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"

# Run the server (prints the URL):
opspilot
# → http://127.0.0.1:8050
```

Then open the URL, drag in `examples/orders.csv` and `examples/customers.csv`,
and start asking questions (or writing SQL).

### Works key-free, better with a (free) LLM key

Without a key, OpsPilot is a SQL console + profiler. To enable plain-English
questions, set **one** OpenAI-compatible provider. Grab a free key, pick the
provider, and go:

```bash
# Windows (PowerShell)
$env:OPSPILOT_LLM_PROVIDER = "nvidia"      # nvidia | groq | gemini | openrouter | openai
$env:OPSPILOT_LLM_API_KEY  = "nvapi-..."   # your free key
opspilot

# macOS / Linux
export OPSPILOT_LLM_PROVIDER="nvidia"
export OPSPILOT_LLM_API_KEY="nvapi-..."
opspilot
```

| Provider | `OPSPILOT_LLM_PROVIDER` | Free key from | Default model |
|---|---|---|---|
| NVIDIA NIM | `nvidia` | build.nvidia.com | `meta/llama-3.3-70b-instruct` |
| Groq | `groq` | console.groq.com | `llama-3.3-70b-versatile` |
| Google Gemini | `gemini` | aistudio.google.com | `gemini-2.0-flash` |
| OpenRouter | `openrouter` | openrouter.ai | `meta-llama/llama-3.3-70b-instruct:free` |
| OpenAI | `openai` | platform.openai.com | `gpt-4o-mini` |

Override the model with `OPSPILOT_LLM_MODEL`. For any other OpenAI-compatible
endpoint, set `OPSPILOT_LLM_PROVIDER=custom` plus `OPSPILOT_LLM_BASE_URL` and
`OPSPILOT_LLM_MODEL`. The header pill shows the active provider when connected.

---

## Deploy in a day (Docker one-liner)

```bash
docker build -t opspilot .
docker run -p 8050:8050 \
  -e OPSPILOT_LLM_PROVIDER="$OPSPILOT_LLM_PROVIDER" \
  -e OPSPILOT_LLM_API_KEY="$OPSPILOT_LLM_API_KEY" opspilot
```

That's the "deploy anywhere" story — a single self-contained container the
customer can run on a laptop, a VM, or a container service.

---

## Example questions (with the sample data)

`examples/orders.csv` (deliberately messy: NULL amounts, duplicate rows,
mixed-case regions) and `examples/customers.csv` let you exercise joins and the
profiler:

- *Which region had the most orders?*
- *Total revenue by status.*
- *Which customers on the Enterprise plan placed orders?*
- *How many orders are missing an amount?*

The profiler will surface the NULL `amount` column, the constant/low-cardinality
columns, and the duplicate rows up front.

---

## How it maps to FDE skills

| FDE skill | Where OpsPilot shows it |
|---|---|
| Integrating heterogeneous sources | CSV + Excel (multi-sheet) + Parquet into one DuckDB |
| Schema inference on messy data | Auto-typing + per-column profiling + data-health checks |
| LLM with guardrails | NL→SQL constrained to read-only SELECT, validated + capped, **shown to the user** |
| Full-stack delivery | FastAPI backend + single-file vanilla-JS UI |
| Deployment | One `pip install`, one Docker command |

---

## Honesty

Profiling and the SQL console are real and key-free. The natural-language → SQL
step needs an LLM key (any free provider above) — without it, OpsPilot degrades
gracefully to the console rather than pretending. No overclaiming.

---

## Project layout

```
src/opspilot/
  db.py        DuckDB access (read-write ingest, read-only query)
  ingest.py    Load CSV / Parquet / Excel into tables
  profile.py   Schema + data-health profiling
  sqlsafe.py   SELECT-only validation + row cap
  nl2sql.py    Provider-agnostic NL→SQL (OpenAI SDK → any compatible endpoint)
  engine.py    run_sql + ask (with one repair attempt)
  app.py       FastAPI endpoints
  cli.py       `opspilot` entry point
  static/      Single-file light UI
tests/         pytest suite (exercises the no-key paths)
examples/      Sample messy data
docs/PRD.md    Product requirements
```

## License

Apache-2.0. Copyright 2026 Sunny.
