"""Authentication related database models."""

from __future__ import annotations

from datetime import datetime, timezone

from ..extensions import db


class ApiToken(db.Model):
    """API token used for authenticating requests."""

    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="readonly")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = db.Column(db.DateTime, nullable=True)

    def is_active(self) -> bool:
        """Return whether the token is still active."""

        return self.revoked_at is None
