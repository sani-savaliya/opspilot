# OpsPilot — Product Requirements

## Problem

Ops teams accumulate messy operational exports (CSV/Excel/Parquet) from disparate
systems. The people who need answers from that data are typically non-technical
and cannot write SQL, while standing up a proper data warehouse is too slow for a
forward-deployed engagement. There is a gap between "the data exists" and "the ops
person can self-serve answers from it" — measured in days, not weeks.

## Goal

Let a forward-deployed engineer stand up, in a single day, a tool that ingests a
customer's actual messy exports, makes their shape and quality legible, and lets
non-technical staff answer questions in plain English — with the generated SQL
shown so the answer is trustworthy and auditable.

## Users

- **Ops analyst (primary):** non-technical, asks plain-English questions, reads
  tables/charts, trusts answers because the SQL is visible.
- **Forward-deployed engineer (operator):** loads the data, validates the
  profile, deploys the container, optionally adds an API key.

## Core requirements

1. **Ingest heterogeneous files** — CSV, Excel (multi-sheet), Parquet — into
   DuckDB with automatic schema/type inference. Unsupported types fail loudly.
2. **Profile** — per table: row count; per column: type, null %, distinct count,
   3 sample values; data-health issues (null % > 30, constant columns, duplicate
   rows).
3. **Natural-language → SQL** — Claude (`claude-opus-4-8`) generates one
   read-only DuckDB SELECT from the question + schema. One automatic repair
   attempt on execution error.
4. **Safety (two layers)** — read-only DuckDB connection; SELECT-only validation
   (single statement, forbidden-keyword reject) with a row cap.
5. **Transparency** — the generated SQL is always shown and is editable; the SQL
   box doubles as a console with a Run button.
6. **Visualization** — result table; bar chart when the result is one label
   column + one numeric column.
7. **Key-free degradation** — works as a SQL console + profiler with no API key;
   NL answers light up when `ANTHROPIC_API_KEY` is set.
8. **Deploy in a day** — `pip install -e .` for local; one Docker command for
   "anywhere."

## Non-goals

- A persistent multi-tenant data warehouse.
- Write-back / data editing of any kind.
- Authentication / multi-user access control (single-operator tool).
- Arbitrary chart types beyond the simple bar chart.

## Success criteria

- A messy CSV + a related CSV load, profile (surfacing real data-health issues),
  and join cleanly in one SQL query.
- A mutating query is rejected, never executed.
- The server boots and `/api/status` reports table count + Claude state.
- Tests pass without ever calling the real Claude API.
