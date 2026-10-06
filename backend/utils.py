"""
backend/utils.py
================
General helper functions and utilities for the Local GitHub Repository Code Explainer.
Includes timing, path normalization, safe string formatting, and error formatting.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


def normalize_rel_path(path: Path, root: Path) -> str:
    """Return a relative path using forward slashes for cross-platform consistency."""
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def format_bytes(size: int) -> str:
    """Format byte sizes into readable strings."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


@contextmanager
def record_time() -> Generator[dict[str, float], None, None]:
    """Measure elapsed execution time using time.perf_counter()."""
    data = {"elapsed": 0.0}
    start = time.perf_counter()
    try:
        yield data
    finally:
        data["elapsed"] = time.perf_counter() - start
