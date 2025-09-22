"""Tests for the export/import configuration API."""
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
    from backend.app.models.pipelet import Pipelet
    from backend.app.models.workflow import Workflow

    return Config, create_app, db, Pipelet, Workflow


ConfigBase, create_app, db, Pipelet, Workflow = _load_app_dependencies()


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


@pytest.fixture(autouse=True)
def clean_database():
    db.session.query(Pipelet).delete()
    db.session.query(Workflow).delete()
    db.session.commit()
    yield
    db.session.query(Pipelet).delete()
    db.session.query(Workflow).delete()
    db.session.commit()


def _create_pipelet(name: str, event: str = "StartTransaction") -> Pipelet:
    pipelet = Pipelet(name=name, event=event, code="def run(message, context):\n    return message")
    db.session.add(pipelet)
    db.session.commit()
    return pipelet


def _create_workflow(name: str, event: str = "StartTransaction") -> Workflow:
    graph = json.dumps({"nodes": {"1": {"id": 1, "data": {"code": "def run(message, context):\n    return message"}}}})
    workflow = Workflow(name=name, event=event, graph_json=graph)
    db.session.add(workflow)
    db.session.commit()
    return workflow


def test_export_roundtrip(client):
    _create_pipelet("Alpha", "StartTransaction")
    _create_pipelet("Beta", "Authorize")
    created_workflow = _create_workflow("WF-1", "StartTransaction")

    response = client.get("/api/export")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == 1
    assert len(data["pipelets"]) == 2
    assert len(data["workflows"]) == 1

    db.session.query(Pipelet).delete()
    db.session.query(Workflow).delete()
    db.session.commit()

    import_response = client.post("/api/import", json=data)
    assert import_response.status_code == 200
    summary = import_response.get_json()
    assert summary == {"created": 3, "updated": 0}

    assert Pipelet.query.count() == 2
    restored = Pipelet.query.filter_by(name="Alpha").first()
    assert restored is not None
    assert restored.event == "StartTransaction"

    restored_workflow = Workflow.query.filter_by(name=created_workflow.name).first()
    assert restored_workflow is not None
    assert json.loads(restored_workflow.graph_json) == json.loads(created_workflow.graph_json)


def test_import_conflict_without_overwrite(client):
    _create_pipelet("Exists", "Authorize")

    payload = {
        "version": 1,
        "pipelets": [
            {"name": "Exists", "event": "Authorize", "code": "def run(message, context):\n    return message"}
        ],
        "workflows": [],
    }

    response = client.post("/api/import", json=payload)
    assert response.status_code == 409
    data = response.get_json()
    assert "already exists" in data["error"]


def test_import_with_overwrite(client):
    pipelet = _create_pipelet("Overwrite", "Authorize")
    workflow = _create_workflow("WF-Overwrite", "Authorize")

    payload = {
        "version": 1,
        "pipelets": [
            {
                "name": "Overwrite",
                "event": "StartTransaction",
                "code": "def run(message, context):\n    return {'value': 1}",
            }
        ],
        "workflows": [
            {
                "name": "WF-Overwrite",
                "event": "StartTransaction",
                "graph_json": json.dumps({"nodes": {}}),
            }
        ],
    }

    response = client.post("/api/import", json=payload, query_string={"overwrite": "true"})
    assert response.status_code == 200
    summary = response.get_json()
    assert summary == {"created": 0, "updated": 2}

    db.session.refresh(pipelet)
    assert pipelet.event == "StartTransaction"
    assert "return {'value': 1}" in pipelet.code

    db.session.refresh(workflow)
    assert workflow.event == "StartTransaction"
    assert json.loads(workflow.graph_json) == {"nodes": {}}
