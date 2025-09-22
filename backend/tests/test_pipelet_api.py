"""Tests for the Pipelet CRUD and execution API endpoints."""

from __future__ import annotations

import json


def _create_pipelet(client, headers) -> dict[str, object]:
    response = client.post(
        "/api/pipelets",
        json={
            "name": "TestPipelet",
            "event": "Heartbeat",
            "code": "def run(message, context):\n    return message",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.get_json()


def test_create_pipelet(client, admin_headers):
    response = client.post(
        "/api/pipelets",
        json={
            "name": "Alpha",
            "event": "Authorize",
            "code": "def run(message, context):\n    return 1",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Alpha"
    assert data["event"] == "Authorize"
    assert data["code"].startswith("def run")


def test_create_pipelet_duplicate_name(client, admin_headers):
    payload = {
        "name": "Duplicate",
        "event": "BootNotification",
        "code": "def run(message, context):\n    return None",
    }
    assert client.post("/api/pipelets", json=payload, headers=admin_headers).status_code == 201

    response = client.post(
        "/api/pipelets",
        json={**payload, "name": payload["name"].lower()},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_update_and_get_pipelet(client, admin_headers):
    created = _create_pipelet(client, admin_headers)

    update_payload = {
        "name": "UpdatedPipelet",
        "event": "StartTransaction",
        "code": "def run(message, context):\n    return {\"value\": 42}",
    }
    update_response = client.put(
        f"/api/pipelets/{created['id']}", json=update_payload, headers=admin_headers
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["name"] == update_payload["name"]
    assert updated["event"] == update_payload["event"]

    detail_response = client.get(f"/api/pipelets/{created['id']}", headers=admin_headers)
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["name"] == update_payload["name"]
    assert detail["event"] == update_payload["event"]
    assert detail["code"] == update_payload["code"]


def test_pipelet_test_run_success(client, admin_headers):
    created = _create_pipelet(client, admin_headers)

    response = client.post(
        f"/api/pipelets/{created['id']}/test",
        json={"message": {"value": 3}, "context": {"extra": True}},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"] == {"value": 3}
    assert data["debug"] == ""
    assert data["error"] is None

    logs_response = client.get(
        "/api/logs",
        query_string={"source": "pipelet", "limit": 1},
        headers=admin_headers,
    )
    assert logs_response.status_code == 200
    logs = logs_response.get_json()
    assert logs, "expected a run log entry for the pipelet execution"
    payload = json.loads(logs[0]["message"])
    assert payload["pipelet"] == created["name"]
    assert payload["event"] == created["event"]


def test_pipelet_test_run_timeout(client, admin_headers):
    response = client.post(
        "/api/pipelets",
        json={
            "name": "SlowPipelet",
            "event": "StopTransaction",
            "code": "import time\n\ndef run(message, context):\n    time.sleep(2)",
        },
        headers=admin_headers,
    )
    pipelet = response.get_json()

    test_response = client.post(
        f"/api/pipelets/{pipelet['id']}/test",
        json={"message": {}, "timeout": 0.1},
        headers=admin_headers,
    )
    assert test_response.status_code == 200
    data = test_response.get_json()
    assert data["result"] is None
    assert data["error"]["type"] == "Timeout"

