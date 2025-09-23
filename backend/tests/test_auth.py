"""Authentication and authorization tests for the API."""

from __future__ import annotations

import pytest


def _set_protection(client, enabled: bool) -> None:
    response = client.post("/api/auth/protection", json={"enabled": enabled})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert data.get("enabled") is enabled


@pytest.mark.usefixtures("cleanup_tokens")
def test_token_issuance_and_listing(client, admin_headers):
    response = client.post(
        "/api/auth/tokens",
        json={"name": "Readonly Token", "role": "readonly"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    created = response.get_json()
    assert created["role"] == "readonly"
    assert created["token"]

    list_response = client.get("/api/auth/tokens", headers=admin_headers)
    assert list_response.status_code == 200
    tokens = list_response.get_json()
    assert isinstance(tokens, list)
    stored = next(token for token in tokens if token["id"] == created["id"])
    assert "token" not in stored
    assert stored["revoked_at"] is None


def test_api_protection_toggle(client):
    status_response = client.get("/api/auth/protection")
    assert status_response.status_code == 200
    assert status_response.get_json()["enabled"] is False

    open_access = client.get("/api/pipelets")
    assert open_access.status_code == 200

    _set_protection(client, True)
    try:
        protected_access = client.get("/api/pipelets")
        assert protected_access.status_code == 401
    finally:
        _set_protection(client, False)

    restored_access = client.get("/api/pipelets")
    assert restored_access.status_code == 200


def test_access_control_for_roles(client, auth_header_factory):
    _set_protection(client, True)
    try:
        # No token is rejected
        assert client.get("/api/pipelets").status_code == 401
        assert client.get("/api/logs/stream").status_code == 401

        readonly_headers = auth_header_factory(role="readonly")
        list_response = client.get("/api/pipelets", headers=readonly_headers)
        assert list_response.status_code == 200

        create_response = client.post(
            "/api/pipelets",
            json={
                "name": "Limited",
                "event": "Authorize",
                "code": "def run(message, context):\n    return message",
            },
            headers=readonly_headers,
        )
        assert create_response.status_code == 403

        admin_headers = auth_header_factory(role="admin")
        admin_create = client.post(
            "/api/pipelets",
            json={
                "name": "AdminPipelet",
                "event": "Heartbeat",
                "code": "def run(message, context):\n    return message",
            },
            headers=admin_headers,
        )
        assert admin_create.status_code == 201
    finally:
        _set_protection(client, False)


def test_revoked_token_is_rejected(client, admin_headers):
    _set_protection(client, True)
    try:
        issued = client.post(
            "/api/auth/tokens",
            json={"name": "Temp", "role": "readonly"},
            headers=admin_headers,
        )
        token_data = issued.get_json()
        token_value = token_data["token"]
        readonly_headers = {"Authorization": f"Bearer {token_value}"}

        initial_access = client.get("/api/pipelets", headers=readonly_headers)
        assert initial_access.status_code == 200

        revoke = client.delete(
            f"/api/auth/tokens/{token_data['id']}", headers=admin_headers
        )
        assert revoke.status_code == 204

        revoked_access = client.get("/api/pipelets", headers=readonly_headers)
        assert revoked_access.status_code == 401
    finally:
        _set_protection(client, False)


def test_rate_limit_for_pipelet_test_endpoint(client, admin_headers):
    create_pipelet = client.post(
        "/api/pipelets",
        json={
            "name": "RateLimited",
            "event": "Authorize",
            "code": "def run(message, context):\n    return message",
        },
        headers=admin_headers,
    )
    pipelet_id = create_pipelet.get_json()["id"]

    for _ in range(10):
        run_response = client.post(
            f"/api/pipelets/{pipelet_id}/test",
            json={"message": {}},
            headers=admin_headers,
        )
        assert run_response.status_code == 200

    blocked = client.post(
        f"/api/pipelets/{pipelet_id}/test",
        json={"message": {}},
        headers=admin_headers,
    )
    assert blocked.status_code == 429
