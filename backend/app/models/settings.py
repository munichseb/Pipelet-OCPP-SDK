"""Application-wide settings stored in the database."""

from __future__ import annotations

from ..extensions import db


class AppSetting(db.Model):
    """Key/value store for simple application settings."""

    __tablename__ = "app_settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<AppSetting {self.key}={self.value}>"
