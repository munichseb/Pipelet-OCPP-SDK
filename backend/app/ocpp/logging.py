"""Utility helpers for persisting OCPP related logs."""

from __future__ import annotations

from collections.abc import Callable

from flask import Flask

from ..extensions import db
from ..models.logs import RunLog


def persist_run_log(app: Flask, source: str, message: str) -> None:
    """Persist a run log entry without raising exceptions."""
    if not message:
        return

    def _log() -> None:
        entry = RunLog(source=source, message=message)
        db.session.add(entry)
        db.session.commit()

    _run_in_app_context(app, _log)


def _run_in_app_context(app: Flask, func: Callable[[], None]) -> None:
    try:
        with app.app_context():
            func()
    except Exception:  # pragma: no cover - defensive logging helper
        # Logging to stdout/stderr is acceptable fallback.
        app.logger.exception("Failed to persist run log entry")
        with app.app_context():
            db.session.rollback()
