"""Tests for the healthcheck endpoint."""

from __future__ import annotations

from app import Config, create_app


class TestConfig(Config):
    """Configuration used during testing."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ENABLE_OCPP_SERVER = False
    ENABLE_SIM_API = False


def create_test_app():
    """Create an application instance configured for tests."""

    return create_app(TestConfig)


def test_health_endpoint_returns_ok():
    """The healthcheck endpoint should return a JSON payload with status ok."""

    app = create_test_app()
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
