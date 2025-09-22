"""REST API endpoints for managing and testing pipelets."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db, limiter
from ..models.logs import RunLog
from ..models.pipelet import ALLOWED_EVENTS, Pipelet
from ..pipelets.runtime import run_pipelet
from ..utils.auth import require_token

bp = Blueprint("pipelets", __name__)


def _pipelet_to_dict(pipelet: Pipelet) -> dict[str, Any]:
    """Serialize a pipelet model to a JSON compatible dictionary."""

    return {
        "id": pipelet.id,
        "name": pipelet.name,
        "event": pipelet.event,
        "code": pipelet.code,
        "created_at": pipelet.created_at.isoformat() + "Z",
        "updated_at": pipelet.updated_at.isoformat() + "Z",
    }


def _validate_pipelet_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate and normalize incoming pipelet payloads."""

    errors: list[str] = []
    name = (payload.get("name") or "").strip()
    event = (payload.get("event") or "").strip()
    code = payload.get("code") or ""

    if not name:
        errors.append("name is required")

    if not event:
        errors.append("event is required")
    elif event not in ALLOWED_EVENTS:
        errors.append("event is not supported")

    if not isinstance(code, str) or not code.strip():
        errors.append("code is required")
    elif "def run(" not in code:
        errors.append("code must define a run function")

    return {"name": name, "event": event, "code": code}, errors


def _ensure_unique_name(name: str, pipelet_id: int | None = None) -> bool:
    """Check whether the given name is unique across pipelets."""

    query = Pipelet.query.filter(func.lower(Pipelet.name) == name.lower())
    if pipelet_id is not None:
        query = query.filter(Pipelet.id != pipelet_id)
    return not db.session.query(query.exists()).scalar()


@bp.post("/pipelets")
@require_token(role="admin")
def create_pipelet() -> tuple[object, int]:
    payload = request.get_json(force=True, silent=True) or {}
    data, errors = _validate_pipelet_payload(payload)
    if errors:
        return jsonify({"errors": errors}), HTTPStatus.BAD_REQUEST

    if not _ensure_unique_name(data["name"]):
        return jsonify({"error": "pipelet with this name already exists"}), HTTPStatus.CONFLICT

    pipelet = Pipelet(**data)
    db.session.add(pipelet)
    db.session.commit()

    return jsonify(_pipelet_to_dict(pipelet)), HTTPStatus.CREATED


@bp.get("/pipelets")
@require_token()
def list_pipelets() -> tuple[object, int]:
    event_filter = request.args.get("event")
    query = Pipelet.query
    if event_filter:
        query = query.filter_by(event=event_filter)
    pipelets = query.order_by(Pipelet.created_at.desc()).all()
    return jsonify([_pipelet_to_dict(pipelet) for pipelet in pipelets]), HTTPStatus.OK


@bp.get("/pipelets/<int:pipelet_id>")
@require_token()
def get_pipelet(pipelet_id: int) -> tuple[object, int]:
    pipelet = Pipelet.query.get_or_404(pipelet_id)
    return jsonify(_pipelet_to_dict(pipelet)), HTTPStatus.OK


@bp.put("/pipelets/<int:pipelet_id>")
@require_token(role="admin")
def update_pipelet(pipelet_id: int) -> tuple[object, int]:
    pipelet = Pipelet.query.get_or_404(pipelet_id)
    payload = request.get_json(force=True, silent=True) or {}
    data, errors = _validate_pipelet_payload(payload)
    if errors:
        return jsonify({"errors": errors}), HTTPStatus.BAD_REQUEST

    if not _ensure_unique_name(data["name"], pipelet.id):
        return jsonify({"error": "pipelet with this name already exists"}), HTTPStatus.CONFLICT

    pipelet.name = data["name"]
    pipelet.event = data["event"]
    pipelet.code = data["code"]
    db.session.commit()

    return jsonify(_pipelet_to_dict(pipelet)), HTTPStatus.OK


@bp.delete("/pipelets/<int:pipelet_id>")
@require_token(role="admin")
def delete_pipelet(pipelet_id: int) -> tuple[object, int]:
    pipelet = Pipelet.query.get_or_404(pipelet_id)
    db.session.delete(pipelet)
    db.session.commit()
    return "", HTTPStatus.NO_CONTENT


@bp.post("/pipelets/<int:pipelet_id>/test")
@require_token(role="admin")
@limiter.limit("10 per minute")
def test_pipelet(pipelet_id: int) -> tuple[object, int]:
    pipelet = Pipelet.query.get_or_404(pipelet_id)
    payload = request.get_json(force=True, silent=True) or {}

    message = payload.get("message") or {}
    context = payload.get("context") or {}
    timeout = payload.get("timeout")

    if not isinstance(message, dict):
        return jsonify({"error": "message must be an object"}), HTTPStatus.BAD_REQUEST
    if not isinstance(context, dict):
        return jsonify({"error": "context must be an object"}), HTTPStatus.BAD_REQUEST
    if timeout is not None:
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            return jsonify({"error": "timeout must be a number"}), HTTPStatus.BAD_REQUEST
    else:
        timeout = 1.5

    result, debug, error = run_pipelet(pipelet.code, message, context, timeout=timeout)

    log_payload: dict[str, Any] = {
        "pipelet": pipelet.name,
        "event": pipelet.event,
        "debug": debug,
        "error": error,
    }
    run_log = RunLog(source="pipelet", message=json.dumps(log_payload))
    db.session.add(run_log)
    db.session.commit()

    response: dict[str, Any] = {
        "result": result,
        "debug": debug,
        "error": error,
    }
    return jsonify(response), HTTPStatus.OK

