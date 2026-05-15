"""Test environment isolation."""

from __future__ import annotations

import os


# Keep the developer's root .env from turning deterministic tests into live GPT/API runs.
os.environ.setdefault("GPT_DRAFTING", "0")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("OPENAI_INTERPRETER_MODEL", "gpt-test")
