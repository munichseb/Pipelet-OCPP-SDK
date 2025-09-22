"""REST endpoints for API token management."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models.auth import ApiToken
from ..utils.auth import generate_token, hash_token, require_token

bp = Blueprint("auth", __name__)


def _serialize(token: ApiToken) -> dict[str, object | None]:
    return {
        "id": token.id,
        "name": token.name,
        "role": token.role,
        "created_at": token.created_at.isoformat() + "Z",
        "revoked_at": token.revoked_at.isoformat() + "Z" if token.revoked_at else None,
    }


@bp.post("/auth/tokens")
@require_token(role="admin")
def create_token() -> tuple[object, int]:
    payload = request.get_json(force=True, silent=True) or {}
    name = (payload.get("name") or "").strip()
    role = (payload.get("role") or "readonly").strip().lower()

    if not name:
        return jsonify({"error": "name is required"}), HTTPStatus.BAD_REQUEST

    if role not in {"admin", "readonly"}:
        return jsonify({"error": "role must be 'admin' or 'readonly'"}), HTTPStatus.BAD_REQUEST

    plaintext = generate_token()
    token = ApiToken(name=name, role=role, token_hash=hash_token(plaintext))
    db.session.add(token)
    db.session.commit()

    response_payload = _serialize(token)
    response_payload["token"] = plaintext
    return jsonify(response_payload), HTTPStatus.CREATED


@bp.get("/auth/tokens")
@require_token(role="admin")
def list_tokens() -> tuple[object, int]:
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    return jsonify([_serialize(token) for token in tokens]), HTTPStatus.OK


@bp.delete("/auth/tokens/<int:token_id>")
@require_token(role="admin")
def revoke_token(token_id: int) -> tuple[object, int]:
    token = ApiToken.query.get_or_404(token_id)
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        db.session.commit()
    return "", HTTPStatus.NO_CONTENT
