"""API endpoint exposing run log entries."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from ..models.logs import RunLog

bp = Blueprint("logs", __name__)


@bp.get("/logs")
def get_logs() -> tuple[object, int]:
    source = request.args.get("source")
    limit = request.args.get("limit", type=int) or 200
    limit = max(1, min(limit, 200))

    query = RunLog.query
    if source:
        query = query.filter_by(source=source)

    entries = (
        query.order_by(RunLog.created_at.desc()).limit(limit).all()
    )

    data = [
        {
            "id": entry.id,
            "source": entry.source,
            "message": entry.message,
            "createdAt": entry.created_at.isoformat() + "Z",
        }
        for entry in entries
    ]
    return jsonify(data), HTTPStatus.OK
