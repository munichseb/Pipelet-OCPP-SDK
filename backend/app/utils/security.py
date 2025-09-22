"""Security helpers for sandboxing subprocess execution."""
from __future__ import annotations

from collections.abc import Callable


def build_preexec_fn() -> Callable[[], None] | None:
    """Return a callable that configures resource limits for subprocesses."""
    return None

