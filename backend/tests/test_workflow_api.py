"""Tests for the workflow persistence REST API."""

from __future__ import annotations


def test_workflow_roundtrip(client, admin_headers):
    create_response = client.post(
        "/api/workflows", json={"name": "Pipeline"}, headers=admin_headers
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["name"] == "Pipeline"
    assert created["graph_json"] == {}

    list_response = client.get("/api/workflows", headers=admin_headers)
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert any(workflow["id"] == created["id"] for workflow in listed)

    detail_response = client.get(
        f"/api/workflows/{created['id']}", headers=admin_headers
    )
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["name"] == "Pipeline"
    assert detail["graph_json"] == {}

    graph_payload = {"nodes": [], "links": []}
    update_response = client.put(
        f"/api/workflows/{created['id']}",
        json={"graph_json": graph_payload},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["graph_json"] == graph_payload


def test_workflow_name_must_be_unique(client, admin_headers):
    first = client.post("/api/workflows", json={"name": "Alpha"}, headers=admin_headers)
    assert first.status_code == 201

    conflict = client.post(
        "/api/workflows", json={"name": "alpha"}, headers=admin_headers
    )
    assert conflict.status_code == 409

    second = client.post(
        "/api/workflows", json={"name": "Beta"}, headers=admin_headers
    )
    assert second.status_code == 201
    second_data = second.get_json()

    rename_conflict = client.put(
        f"/api/workflows/{second_data['id']}",
        json={"name": "ALPHA", "graph_json": {"nodes": []}},
        headers=admin_headers,
    )
    assert rename_conflict.status_code == 409


def test_update_requires_graph(client, admin_headers):
    created = client.post(
        "/api/workflows", json={"name": "NeedsGraph"}, headers=admin_headers
    )
    workflow_id = created.get_json()["id"]

    missing_payload = client.put(
        f"/api/workflows/{workflow_id}", json={}, headers=admin_headers
    )
    assert missing_payload.status_code == 400
    assert "graph_json" in " ".join(missing_payload.get_json().get("errors", []))


def test_workflow_event_binding(client, admin_headers):
    created = client.post(
        "/api/workflows", json={"name": "Binding"}, headers=admin_headers
    )
    workflow_id = created.get_json()["id"]

    bind_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": "StartTransaction"},
        headers=admin_headers,
    )
    assert bind_response.status_code == 200
    bound = bind_response.get_json()
    assert bound["event"] == "StartTransaction"

    invalid_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": "Unknown"},
        headers=admin_headers,
    )
    assert invalid_response.status_code == 400

    other = client.post(
        "/api/workflows", json={"name": "Other"}, headers=admin_headers
    )
    other_id = other.get_json()["id"]
    conflict = client.put(
        f"/api/workflows/{other_id}/event",
        json={"event": "StartTransaction"},
        headers=admin_headers,
    )
    assert conflict.status_code == 409

    unbind_response = client.put(
        f"/api/workflows/{workflow_id}/event",
        json={"event": None},
        headers=admin_headers,
    )
    assert unbind_response.status_code == 200
    assert unbind_response.get_json()["event"] is None

    bindings_response = client.get(
        "/api/workflows/bindings", headers=admin_headers
    )
    assert bindings_response.status_code == 200
    assert bindings_response.get_json() == []
