"""Natural-language -> DuckDB SQL via any OpenAI-compatible provider.

OpsPilot is provider-agnostic: NVIDIA NIM, Groq, Google Gemini, OpenRouter and
OpenAI all expose the same ``/chat/completions`` shape, so a single OpenAI SDK
client points at whichever one you configure. All have free tiers.

Configure with environment variables::

    OPSPILOT_LLM_PROVIDER  nvidia | groq | gemini | openrouter | openai | custom
    OPSPILOT_LLM_API_KEY   your key (or a provider-specific key, see PRESETS)
    OPSPILOT_LLM_MODEL     optional override of the provider's default model
    OPSPILOT_LLM_BASE_URL  required only for provider=custom

Key-free safe: with no key, ``llm_enabled`` is False and the app falls back to
the SQL console + profiler. Errors surface as ``NL2SQLError``.
"""

from __future__ import annotations

import os
import re

# provider -> (base_url, default_model, fallback_key_env_vars)
PRESETS: dict[str, tuple[str | None, str, tuple[str, ...]]] = {
    "nvidia": (
        "https://integrate.api.nvidia.com/v1",
        "meta/llama-3.3-70b-instruct",
        ("NVIDIA_API_KEY", "NGC_API_KEY"),
    ),
    "groq": (
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
        ("GROQ_API_KEY",),
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.0-flash",
        ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "meta-llama/llama-3.3-70b-instruct:free",
        ("OPENROUTER_API_KEY",),
    ),
    "openai": (None, "gpt-4o-mini", ("OPENAI_API_KEY",)),
    "custom": (None, "", ()),
}
DEFAULT_PROVIDER = "nvidia"

NO_KEY_MESSAGE = (
    "No AI provider configured. Set OPSPILOT_LLM_API_KEY (free keys: NVIDIA "
    "build.nvidia.com, Groq console.groq.com, Google AI Studio) — or use the "
    "SQL console below."
)

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


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _config() -> tuple[str, str | None, str, str]:
    """Resolve (provider, base_url, model, api_key) from the environment."""
    provider = (_env("OPSPILOT_LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
    base_default, model_default, key_envs = PRESETS.get(
        provider, PRESETS[DEFAULT_PROVIDER]
    )
    base_url = _env("OPSPILOT_LLM_BASE_URL") or base_default
    model = _env("OPSPILOT_LLM_MODEL") or model_default
    api_key = _env("OPSPILOT_LLM_API_KEY")
    if not api_key:
        for env_name in key_envs:
            if _env(env_name):
                api_key = _env(env_name)
                break
    return provider, base_url, model, api_key


def llm_enabled() -> bool:
    """True when an API key is configured for the active provider."""
    return bool(_config()[3])


def provider_label() -> str:
    """Short human label for the active provider, e.g. 'nvidia'."""
    return _config()[0]


def _strip_fences(text: str) -> str:
    """Remove ```sql ... ``` fences and trailing semicolons if present."""
    stripped = text.strip()
    fence = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    return stripped


def _call_llm(system: str, user_content: str) -> str:
    """Make one chat-completions call and return stripped SQL text."""
    provider, base_url, model, api_key = _config()
    if not api_key:
        raise NL2SQLError(NO_KEY_MESSAGE)
    if not model:
        raise NL2SQLError("Set OPSPILOT_LLM_MODEL for a custom provider.")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency is required
        raise NL2SQLError("The 'openai' package is not installed.") from exc

    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=800,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        sql = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 - auth/network errors surface clearly
        raise NL2SQLError(f"{provider} request failed: {exc}") from exc

    sql = _strip_fences(sql)
    if not sql:
        raise NL2SQLError(f"{provider} returned an empty query.")
    return sql


def question_to_sql(schema_text: str, question: str) -> str:
    """Translate a plain-English question into a DuckDB SELECT query."""
    if not llm_enabled():
        raise NL2SQLError(NO_KEY_MESSAGE)
    user = f"Schema:\n{schema_text}\n\nQuestion: {question}"
    return _call_llm(SYSTEM_PROMPT, user)


def repair_sql(schema_text: str, question: str, sql: str, error: str) -> str:
    """Ask the model to fix a query that failed to execute."""
    if not llm_enabled():
        raise NL2SQLError(NO_KEY_MESSAGE)
    user = (
        f"Schema:\n{schema_text}\n\n"
        f"Question: {question}\n\n"
        f"Failing query:\n{sql}\n\n"
        f"Error:\n{error}"
    )
    return _call_llm(REPAIR_SYSTEM_PROMPT, user)
