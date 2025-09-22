"""Helper utilities for API token based authentication."""

from __future__ import annotations

import functools
import hashlib
import hmac
import secrets
from http import HTTPStatus
from typing import Any, Callable, TypeVar, cast

from flask import g, jsonify, request

from ..models.auth import ApiToken

TCallable = TypeVar("TCallable", bound=Callable[..., Any])

_ROLE_LEVEL = {"readonly": 0, "admin": 1}


def hash_token(token: str) -> str:
    """Return a SHA-256 hash for the given token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    """Generate a secure random token string."""

    return secrets.token_urlsafe(32)


def _extract_bearer_token() -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value.strip()


def _find_token(token_hash: str) -> ApiToken | None:
    return ApiToken.query.filter_by(token_hash=token_hash).first()


def _unauthorized(message: str):
    response = jsonify({"error": message})
    response.status_code = HTTPStatus.UNAUTHORIZED
    response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _forbidden(message: str):
    return jsonify({"error": message}), HTTPStatus.FORBIDDEN


def _role_allows(token_role: str, required_role: str) -> bool:
    token_level = _ROLE_LEVEL.get(token_role, -1)
    required_level = _ROLE_LEVEL.get(required_role, 0)
    return token_level >= required_level


def require_token(role: str = "readonly") -> Callable[[TCallable], TCallable]:
    """Decorator enforcing API token authentication with the given role."""

    def decorator(func: TCallable) -> TCallable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            token_value = _extract_bearer_token()
            if not token_value:
                return _unauthorized("missing bearer token")

            token_hash = hash_token(token_value)
            api_token = _find_token(token_hash)
            if api_token is None:
                return _unauthorized("invalid token")

            if not api_token.is_active():
                return _unauthorized("token revoked")

            if not _role_allows(api_token.role, role):
                return _forbidden("insufficient role")

            if not hmac.compare_digest(token_hash, api_token.token_hash):
                return _unauthorized("invalid token")

            g.api_token = api_token

            return func(*args, **kwargs)

        return cast(TCallable, wrapper)

    return decorator
