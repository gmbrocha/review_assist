"""Environment loading for optional GPT-backed drafting."""

from __future__ import annotations

import os
from pathlib import Path

from .source_catalog import repo_root


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"", "0", "false", "no", "off"}
DEFAULT_GPT_MODEL = "gpt-5.5"
DEFAULT_GPT_DRAFTING_WORKERS = 2
DEFAULT_GPT_DRAFT_MAX_PAYLOAD_BYTES = 60000


class GptConfigurationError(RuntimeError):
    """Raised when GPT drafting is requested but configuration is incomplete."""


def load_project_env() -> None:
    """Load root .env values without overriding process environment values."""

    env_path = repo_root() / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_file_fallback(env_path)
        return
    load_dotenv(env_path, override=False)


def gpt_drafting_enabled() -> bool:
    load_project_env()
    return _truthy(os.environ.get("GPT_DRAFTING"))


def resolve_gpt_model(cli_model: str | None = None) -> str:
    load_project_env()
    if cli_model and cli_model.strip():
        return cli_model.strip()
    configured = os.environ.get("OPENAI_INTERPRETER_MODEL", "").strip()
    return configured or DEFAULT_GPT_MODEL


def openai_api_key_required() -> str:
    load_project_env()
    value = os.environ.get("OPENAI_API_KEY", "").strip()
    if not value:
        raise GptConfigurationError("GPT drafting is enabled but OPENAI_API_KEY is not configured.")
    return value


def gpt_drafting_workers() -> int:
    load_project_env()
    return _bounded_int(
        os.environ.get("GPT_DRAFTING_WORKERS"),
        default=DEFAULT_GPT_DRAFTING_WORKERS,
        minimum=1,
        maximum=8,
    )


def gpt_draft_max_payload_bytes() -> int:
    load_project_env()
    return _bounded_int(
        os.environ.get("GPT_DRAFT_MAX_PAYLOAD_BYTES"),
        default=DEFAULT_GPT_DRAFT_MAX_PAYLOAD_BYTES,
        minimum=10000,
        maximum=500000,
    )


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return False


def _load_env_file_fallback(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _unquote(value.strip())


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _bounded_int(value: str | None, *, default: int, minimum: int, maximum: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))
