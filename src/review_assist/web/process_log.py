"""Small in-memory process log for the local web UI."""

from __future__ import annotations

import re
import threading
from collections import deque
from datetime import datetime
from typing import Any


MAX_LOG_LINES = 500
DEFAULT_TAIL = 50
_MAX_MESSAGE_LENGTH = 500
_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s]+")


class ProcessLog:
    """Thread-safe rolling process log for local developer observability."""

    def __init__(self, max_lines: int = MAX_LOG_LINES) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_lines)
        self._active_count = 0
        self._lock = threading.Lock()

    def append(self, event: str, message: str = "", **metadata: Any) -> dict[str, Any]:
        """Append one sanitized log line."""

        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_event = _sanitize_token(event)
        clean_metadata = {key: _sanitize_value(value) for key, value in metadata.items() if value not in (None, "")}
        clean_message = _sanitize_message(message)
        line = _format_line(timestamp, clean_event, clean_message, clean_metadata)
        entry = {
            "timestamp": timestamp,
            "event": clean_event,
            "message": clean_message,
            "metadata": clean_metadata,
            "line": line,
        }
        with self._lock:
            self._entries.append(entry)
        return entry

    def start(self, event: str, message: str = "started", **metadata: Any) -> None:
        """Mark a web process as active and append its start line."""

        with self._lock:
            self._active_count += 1
        self.append(event, message, **metadata)

    def finish(self, event: str, message: str = "complete", **metadata: Any) -> None:
        """Mark a web process as finished and append its completion line."""

        self.append(event, message, **metadata)
        with self._lock:
            self._active_count = max(0, self._active_count - 1)

    def tail(self, count: int = DEFAULT_TAIL) -> dict[str, Any]:
        """Return the latest log entries."""

        bounded = max(1, min(int(count or DEFAULT_TAIL), MAX_LOG_LINES))
        with self._lock:
            entries = list(self._entries)[-bounded:]
            active = self._active_count > 0
        return {
            "active": active,
            "tail": bounded,
            "entries": entries,
            "lines": [entry["line"] for entry in entries],
        }


process_log = ProcessLog()


def append_process_log(event: str, message: str = "", **metadata: Any) -> dict[str, Any]:
    """Append a line to the shared web process log."""

    return process_log.append(event, message, **metadata)


def get_process_log_tail(count: int = DEFAULT_TAIL) -> dict[str, Any]:
    """Return the latest shared web process log lines."""

    return process_log.tail(count)


def _format_line(timestamp: str, event: str, message: str, metadata: dict[str, Any]) -> str:
    pieces = [f"[{timestamp}]", event]
    if message:
        pieces.append(message)
    for key, value in metadata.items():
        pieces.append(f"{key}={value}")
    return " ".join(pieces)


def _sanitize_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(value or "process").strip())
    return token[:80] or "process"


def _sanitize_message(value: str) -> str:
    text = " ".join(str(value or "").split())
    text = _PATH_RE.sub("[local_path]", text)
    return text[:_MAX_MESSAGE_LENGTH]


def _sanitize_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple | set):
        return ",".join(_sanitize_value(item) for item in list(value)[:8])
    text = " ".join(str(value or "").split())
    text = _PATH_RE.sub("[local_path]", text)
    return text[:160]
