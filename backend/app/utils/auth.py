"""Helper utilities for API token based authentication."""

from __future__ import annotations

import functools
import hashlib
import hmac
import secrets
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeVar, cast

from flask import g, jsonify, request

from ..models.auth import ApiToken
from ..models.settings import AppSetting
from ..extensions import db

TCallable = TypeVar("TCallable", bound=Callable[..., Any])

_ROLE_LEVEL = {"readonly": 0, "admin": 1}
_API_PROTECTION_SETTING_KEY = "api_auth_protection"


def _normalize_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def normalize_token_protection_value(value: object) -> bool:
    """Normalize arbitrary payload to a boolean flag."""

    return _normalize_bool(value)


def is_token_protection_enabled() -> bool:
    """Return whether API token protection is currently enforced."""

    cached = getattr(g, "_api_protection_enabled", None)
    if isinstance(cached, bool):
        return cached

    setting = AppSetting.query.filter_by(key=_API_PROTECTION_SETTING_KEY).first()
    enabled = False
    if setting is not None:
        enabled = _normalize_bool(setting.value)

    g._api_protection_enabled = enabled
    return enabled


def set_token_protection_enabled(enabled: bool) -> None:
    """Persist whether API token protection should be enforced."""

    setting = AppSetting.query.filter_by(key=_API_PROTECTION_SETTING_KEY).first()
    value = "true" if enabled else "false"
    if setting is None:
        setting = AppSetting(key=_API_PROTECTION_SETTING_KEY, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    db.session.commit()
    g._api_protection_enabled = enabled


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
            if not is_token_protection_enabled():
                return func(*args, **kwargs)

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
