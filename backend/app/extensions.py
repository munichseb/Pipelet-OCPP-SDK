"""Extensions used by the Flask application."""

from flask import g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy


def _limiter_key_func() -> str:
    token = getattr(g, "api_token", None)
    if token is not None:
        return f"token:{token.id}"
    return get_remote_address()


db = SQLAlchemy()
cors = CORS()
limiter = Limiter(key_func=_limiter_key_func, default_limits=[])

__all__ = ["db", "cors", "limiter"]
