"""Natural-language -> DuckDB SQL via the official Anthropic SDK.

Key-free safe: when ANTHROPIC_API_KEY is unset, ``claude_enabled`` returns
False and the app falls back to the SQL console. When set, ``question_to_sql``
asks Claude (model ``claude-opus-4-8``) for a single read-only SELECT.

Per the OpsPilot spec, the request passes NO temperature/top_p/budget_tokens —
those 400 on this model. Errors from the SDK are surfaced as ``NL2SQLError``.
"""

from __future__ import annotations

import os
import re

MODEL = "claude-opus-4-8"
SYSTEM_PROMPT = (
    "You are a DuckDB SQL expert. Given the schema, translate the user's "
    "question into ONE read-only DuckDB SELECT query. Output ONLY the SQL, no "
    "prose, no markdown fences, no semicolon."
)
REPAIR_SYSTEM_PROMPT = (
    "You are a DuckDB SQL expert. A previous query failed. Given the schema, "
    "the failing query, and the error, output ONE corrected read-only DuckDB "
    "SELECT query. Output ONLY the SQL, no prose, no markdown fences, no semicolon."
)


class NL2SQLError(RuntimeError):
    """Raised when natural-language translation fails or is unavailable."""


def claude_enabled() -> bool:
    """True when an Anthropic API key is configured in the environment."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _strip_fences(text: str) -> str:
    """Remove ```sql ... ``` fences and trailing semicolons if present."""
    stripped = text.strip()
    fence = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    return stripped


def _call_claude(system: str, user_content: str) -> str:
    """Make a single Messages API call and return stripped SQL text."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - dependency is required
        raise NL2SQLError("The 'anthropic' package is not installed.") from exc

    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        sql = "".join(b.text for b in resp.content if b.type == "text").strip()
    except anthropic.APIError as exc:
        raise NL2SQLError(f"Claude API error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - auth/config errors surface clearly
        raise NL2SQLError(f"Claude request failed: {exc}") from exc

    sql = _strip_fences(sql)
    if not sql:
        raise NL2SQLError("Claude returned an empty query.")
    return sql


def question_to_sql(schema_text: str, question: str) -> str:
    """Translate a plain-English question into a DuckDB SELECT query."""
    if not claude_enabled():
        raise NL2SQLError(
            "Set ANTHROPIC_API_KEY for natural-language questions."
        )
    user = f"Schema:\n{schema_text}\n\nQuestion: {question}"
    return _call_claude(SYSTEM_PROMPT, user)


def repair_sql(schema_text: str, question: str, sql: str, error: str) -> str:
    """Ask Claude to fix a query that failed to execute."""
    if not claude_enabled():
        raise NL2SQLError(
            "Set ANTHROPIC_API_KEY for natural-language questions."
        )
    user = (
        f"Schema:\n{schema_text}\n\n"
        f"Question: {question}\n\n"
        f"Failing query:\n{sql}\n\n"
        f"Error:\n{error}"
    )
    return _call_claude(REPAIR_SYSTEM_PROMPT, user)
