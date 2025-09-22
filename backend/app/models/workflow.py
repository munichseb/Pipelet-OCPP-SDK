"""Workflow model definition."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class Workflow(db.Model):
    """Represents an executable workflow graph."""

    __tablename__ = "workflows"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    graph_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - repr not critical for tests
        return f"<Workflow {self.name!r}>"
