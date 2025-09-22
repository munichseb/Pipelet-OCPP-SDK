"""Tests for the Pipelet CRUD and execution API endpoints."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest
from sqlalchemy.pool import StaticPool

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_app_dependencies():
    from app import Config, create_app
    from backend.app.extensions import db

    return Config, create_app, db


ConfigBase, create_app, db = _load_app_dependencies()


class TestConfig(ConfigBase):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    ENABLE_OCPP_SERVER = False
    ENABLE_SIM_API = False


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


def _create_pipelet(client) -> dict[str, object]:
    response = client.post(
        "/api/pipelets",
        json={
            "name": "TestPipelet",
            "event": "Heartbeat",
            "code": "def run(message, context):\n    return message",
        },
    )
    assert response.status_code == 201
    return response.get_json()


def test_create_pipelet(client):
    response = client.post(
        "/api/pipelets",
        json={
            "name": "Alpha",
            "event": "Authorize",
            "code": "def run(message, context):\n    return 1",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Alpha"
    assert data["event"] == "Authorize"
    assert data["code"].startswith("def run")


def test_create_pipelet_duplicate_name(client):
    payload = {
        "name": "Duplicate",
        "event": "BootNotification",
        "code": "def run(message, context):\n    return None",
    }
    assert client.post("/api/pipelets", json=payload).status_code == 201

    response = client.post(
        "/api/pipelets",
        json={**payload, "name": payload["name"].lower()},
    )

    assert response.status_code == 409


def test_update_and_get_pipelet(client):
    created = _create_pipelet(client)

    update_payload = {
        "name": "UpdatedPipelet",
        "event": "StartTransaction",
        "code": "def run(message, context):\n    return {\"value\": 42}",
    }
    update_response = client.put(
        f"/api/pipelets/{created['id']}", json=update_payload
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["name"] == update_payload["name"]
    assert updated["event"] == update_payload["event"]

    detail_response = client.get(f"/api/pipelets/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["name"] == update_payload["name"]
    assert detail["event"] == update_payload["event"]
    assert detail["code"] == update_payload["code"]


def test_pipelet_test_run_success(client):
    created = _create_pipelet(client)

    response = client.post(
        f"/api/pipelets/{created['id']}/test",
        json={"message": {"value": 3}, "context": {"extra": True}},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"] == {"value": 3}
    assert data["debug"] == ""
    assert data["error"] is None

    logs_response = client.get("/api/logs", query_string={"source": "pipelet", "limit": 1})
    assert logs_response.status_code == 200
    logs = logs_response.get_json()
    assert logs, "expected a run log entry for the pipelet execution"
    payload = json.loads(logs[0]["message"])
    assert payload["pipelet"] == created["name"]
    assert payload["event"] == created["event"]


def test_pipelet_test_run_timeout(client):
    response = client.post(
        "/api/pipelets",
        json={
            "name": "SlowPipelet",
            "event": "StopTransaction",
            "code": "import time\n\ndef run(message, context):\n    time.sleep(2)",
        },
    )
    pipelet = response.get_json()

    test_response = client.post(
        f"/api/pipelets/{pipelet['id']}/test",
        json={"message": {}, "timeout": 0.1},
    )
    assert test_response.status_code == 200
    data = test_response.get_json()
    assert data["result"] is None
    assert data["error"]["type"] == "Timeout"

