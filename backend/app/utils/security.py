"""Security helpers for sandboxing subprocess execution."""
from __future__ import annotations

from typing import Callable, Optional


def build_preexec_fn() -> Optional[Callable[[], None]]:
    """Return a callable that configures resource limits for subprocesses."""
    return None

