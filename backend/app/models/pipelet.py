"""Pipelet model definition."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db

ALLOWED_EVENTS = [
    "BootNotification",
    "Heartbeat",
    "Authorize",
    "StartTransaction",
    "StopTransaction",
]


class Pipelet(db.Model):
    """Represents a Pipelet definition."""

    __tablename__ = "pipelets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    event = db.Column(db.String(255), nullable=False)
    code = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - repr not critical for tests
        return f"<Pipelet {self.name!r}>"
