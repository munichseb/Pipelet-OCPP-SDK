"""Configuration for the Pipelet OCPP backend."""

from __future__ import annotations

import os


class Config:
    """Base configuration for the Flask application."""

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "mysql+pymysql://app:app@localhost:3306/pipelet_sandbox"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    JSONIFY_PRETTYPRINT_REGULAR: bool = False
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    DB_INIT_MAX_RETRIES: int = int(os.getenv("DB_INIT_MAX_RETRIES", "30"))
    DB_INIT_RETRY_DELAY: float = float(os.getenv("DB_INIT_RETRY_DELAY", "2"))
