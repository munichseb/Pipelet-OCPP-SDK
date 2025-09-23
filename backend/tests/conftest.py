from __future__ import annotations

import pathlib
import secrets
import sys
from collections.abc import Callable

import pytest
from sqlalchemy.pool import StaticPool

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_dependencies():
    from app import Config, create_app
    from backend.app.extensions import db

    return Config, create_app, db


ConfigBase, create_app, db = _load_dependencies()


class TestConfig(ConfigBase):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    ENABLE_OCPP_SERVER = False
    ENABLE_SIM_API = False
    CORS_ALLOWED_ORIGINS = "http://localhost"


@pytest.fixture(scope="module")
def app():
    app = create_app(TestConfig)
    ctx = app.app_context()
    ctx.push()
    yield app
    db.session.remove()
    ctx.pop()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_header_factory(app):
    from backend.app.models.auth import ApiToken
    from backend.app.utils.auth import hash_token

    created_tokens: list[ApiToken] = []

    def factory(role: str = "admin", name: str | None = None) -> dict[str, str]:
        token_value = secrets.token_urlsafe(16)
        token = ApiToken(
            name=name or f"Test {role.title()} Token",
            role=role,
            token_hash=hash_token(token_value),
        )
        db.session.add(token)
        db.session.commit()
        created_tokens.append(token)
        return {"Authorization": f"Bearer {token_value}"}

    yield factory

    for token in created_tokens:
        db.session.delete(token)
    db.session.commit()


@pytest.fixture(autouse=True)
def cleanup_tokens(app):
    from backend.app.models.auth import ApiToken
    from backend.app.models.settings import AppSetting

    yield

    db.session.query(ApiToken).delete()
    db.session.query(AppSetting).delete()
    db.session.commit()


@pytest.fixture()
def admin_headers(auth_header_factory: Callable[..., dict[str, str]]):
    return auth_header_factory(role="admin")


@pytest.fixture()
def readonly_headers(auth_header_factory: Callable[..., dict[str, str]]):
    return auth_header_factory(role="readonly")
