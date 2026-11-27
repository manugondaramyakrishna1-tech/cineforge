"""Small reliability helpers for CineForge file-based workflows.

These helpers avoid destructive overwrites and provide bounded retries. They do
not launch external media executables.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def atomic_write_text(path: str | Path, content: str, *, encoding: str = "utf-8") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        temporary.write_text(content, encoding=encoding)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)
    return destination


def atomic_write_json(path: str | Path, payload: object) -> Path:
    return atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


def retry_call(operation: Callable[[], T], *, attempts: int = 3, delay_seconds: float = 0.5,
                retry_on: tuple[type[BaseException], ...] = (OSError,)) -> T:
    """Retry selected transient exceptions with bounded exponential backoff."""
    if attempts < 1 or attempts > 5:
        raise ValueError("attempts must be between 1 and 5")
    if delay_seconds < 0 or delay_seconds > 5:
        raise ValueError("delay_seconds must be between 0 and 5")
    for attempt in range(attempts):
        try:
            return operation()
        except retry_on:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_seconds * (2 ** attempt))
    raise RuntimeError("retry loop ended unexpectedly")


def recover_json(path: str | Path, default: object = None) -> object:
    """Read JSON safely; return a caller-provided default on damaged/missing files."""
    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default
