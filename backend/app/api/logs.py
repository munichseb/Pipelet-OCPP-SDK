"""API endpoints exposing run log entries."""

from __future__ import annotations

import json
import time
from http import HTTPStatus
from typing import Iterable

from flask import Blueprint, Response, jsonify, request, stream_with_context

from ..models.logs import RunLog

bp = Blueprint("logs", __name__)

_VALID_SOURCES = {"cp", "cs", "pipelet"}


def _serialize_entry(entry: RunLog) -> dict[str, object]:
    return {
        "id": entry.id,
        "source": entry.source,
        "message": entry.message,
        "createdAt": entry.created_at.isoformat() + "Z",
    }


def _filter_by_source(query, source: str | None):
    if source:
        if source not in _VALID_SOURCES:
            return None
        query = query.filter_by(source=source)
    return query


@bp.get("/logs")
def get_logs() -> tuple[object, int]:
    source = request.args.get("source")
    limit = request.args.get("limit", type=int) or 200
    limit = max(1, min(limit, 200))

    query = _filter_by_source(RunLog.query, source)
    if query is None:
        return jsonify({"error": "invalid source"}), HTTPStatus.BAD_REQUEST

    entries = query.order_by(RunLog.created_at.desc()).limit(limit).all()
    data = [_serialize_entry(entry) for entry in entries]
    return jsonify(data), HTTPStatus.OK


@bp.get("/logs/download")
def download_logs() -> Response | tuple[object, int]:
    source = request.args.get("source")
    limit = request.args.get("limit", type=int) or 200
    limit = max(1, min(limit, 1000))

    query = _filter_by_source(RunLog.query, source)
    if query is None:
        return jsonify({"error": "invalid source"}), HTTPStatus.BAD_REQUEST

    entries = query.order_by(RunLog.created_at.desc()).limit(limit).all()
    lines = [
        json.dumps(_serialize_entry(entry))
        for entry in reversed(entries)
    ]
    payload = "\n".join(lines)
    response = Response(payload, mimetype="application/x-ndjson")
    response.headers["Content-Disposition"] = "attachment; filename=run-logs.ndjson"
    return response


@bp.get("/logs/stream")
def stream_logs() -> Response | tuple[object, int]:
    source = request.args.get("source")
    query = _filter_by_source(RunLog.query, source)
    if query is None:
        return jsonify({"error": "invalid source"}), HTTPStatus.BAD_REQUEST

    latest = query.order_by(RunLog.id.desc()).first()
    last_id = latest.id if latest is not None else 0

    @stream_with_context
    def event_stream() -> Iterable[str]:
        nonlocal last_id
        yield ": stream-start\n\n"
        while True:
            new_query = _filter_by_source(RunLog.query, source)
            if new_query is None:
                break
            new_entries = (
                new_query.filter(RunLog.id > last_id)
                .order_by(RunLog.id.asc())
                .all()
            )
            for entry in new_entries:
                last_id = entry.id
                payload = json.dumps(_serialize_entry(entry))
                yield f"data: {payload}\n\n"
            if not new_entries:
                yield ": keep-alive\n\n"
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")
