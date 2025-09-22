"""Tests for the workflow persistence REST API."""

from __future__ import annotations

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


def test_workflow_roundtrip(client):
    create_response = client.post("/api/workflows", json={"name": "Pipeline"})
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["name"] == "Pipeline"
    assert created["graph_json"] == {}

    list_response = client.get("/api/workflows")
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert any(workflow["id"] == created["id"] for workflow in listed)

    detail_response = client.get(f"/api/workflows/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["name"] == "Pipeline"
    assert detail["graph_json"] == {}

    graph_payload = {"nodes": [], "links": []}
    update_response = client.put(
        f"/api/workflows/{created['id']}",
        json={"graph_json": graph_payload},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["graph_json"] == graph_payload



def test_workflow_name_must_be_unique(client):
    first = client.post("/api/workflows", json={"name": "Alpha"})
    assert first.status_code == 201

    conflict = client.post("/api/workflows", json={"name": "alpha"})
    assert conflict.status_code == 409

    second = client.post("/api/workflows", json={"name": "Beta"})
    assert second.status_code == 201
    second_data = second.get_json()

    rename_conflict = client.put(
        f"/api/workflows/{second_data['id']}",
        json={"name": "ALPHA", "graph_json": {"nodes": []}},
    )
    assert rename_conflict.status_code == 409


def test_update_requires_graph(client):
    created = client.post("/api/workflows", json={"name": "NeedsGraph"})
    workflow_id = created.get_json()["id"]

    missing_payload = client.put(f"/api/workflows/{workflow_id}", json={})
    assert missing_payload.status_code == 400
    assert "graph_json" in " ".join(missing_payload.get_json().get("errors", []))


def test_workflow_event_binding(client):
    created = client.post("/api/workflows", json={"name": "Binding"})
    workflow_id = created.get_json()["id"]

    bind_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": "StartTransaction"},
    )
    assert bind_response.status_code == 200
    bound = bind_response.get_json()
    assert bound["event"] == "StartTransaction"

    invalid_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": "Unknown"},
    )
    assert invalid_response.status_code == 400

    other = client.post("/api/workflows", json={"name": "Other"})
    other_id = other.get_json()["id"]
    conflict = client.put(
        f"/api/workflows/{other_id}/event",
        json={"event": "StartTransaction"},
    )
    assert conflict.status_code == 409

    unbind_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": None},
    )
    assert unbind_response.status_code == 200
    assert unbind_response.get_json()["event"] is None

    bindings_response = client.get("/api/workflows/bindings")
    assert bindings_response.status_code == 200
    assert bindings_response.get_json() == []

# Import placed at bottom to avoid circular import within test config
