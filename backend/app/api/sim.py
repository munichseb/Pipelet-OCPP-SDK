"""REST triggers for the OCPP charge point simulator."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request

from ..ocpp.simulator import (
    SimulatorState,
    SimulatorStatus,
    get_simulator,
)
from ..utils.auth import require_token

bp = Blueprint("sim", __name__)


def _serialize_state(state: SimulatorState) -> dict[str, object]:
    return {
        "interval": state.interval,
        "transactionId": state.transaction_id,
    }


def _json_error(message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
    return jsonify({"error": message}), status


def _serialize_timestamp(value: object | None) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        timestamp = value.isoformat()
        if timestamp.endswith("+00:00"):
            return timestamp.replace("+00:00", "Z")
        if not timestamp.endswith("Z"):
            return f"{timestamp}Z"
        return timestamp
    return str(value)


def _serialize_status(status: SimulatorStatus) -> dict[str, object | None]:
    return {
        "connected": status.connected,
        "last_event_ts": _serialize_timestamp(status.last_event_ts),
    }


def _require_cp_id() -> str:
    payload = request.get_json(silent=True) or {}
    cp_id = payload.get("cp_id") or payload.get("cpId")
    if not isinstance(cp_id, str) or not cp_id.strip():
        raise ValueError("cp_id is required")
    return cp_id.strip()


def _require_id_tag() -> str:
    payload = request.get_json(silent=True) or {}
    id_tag = payload.get("idTag")
    if not isinstance(id_tag, str) or not id_tag:
        raise ValueError("idTag is required")
    return id_tag


@bp.post("/sim/connect")
@require_token(role="admin")
def connect() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        state = simulator.connect(cp_id)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Simulator connect failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/disconnect")
@require_token(role="admin")
def disconnect() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        _require_cp_id()
        state = simulator.disconnect()
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Simulator disconnect failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/heartbeat/start")
@require_token(role="admin")
def start_heartbeat() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        state = simulator.start_heartbeat(cp_id)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Heartbeat start failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/heartbeat/stop")
@require_token(role="admin")
def stop_heartbeat() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        state = simulator.stop_heartbeat(cp_id)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Heartbeat stop failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/rfid")
@require_token(role="admin")
def authorize() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        id_tag = _require_id_tag()
        state = simulator.authorize(cp_id, id_tag)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Authorize failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/start")
@require_token(role="admin")
def start_transaction() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        id_tag = _require_id_tag()
        state = simulator.start_transaction(cp_id, id_tag)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Start transaction failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/stop")
@require_token(role="admin")
def stop_transaction() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        cp_id = _require_cp_id()
        state = simulator.stop_transaction(cp_id)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Stop transaction failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.get("/sim/status")
@require_token()
def get_status() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    cp_id = request.args.get("cp_id", "CP_1").strip()
    if not cp_id:
        return _json_error("cp_id is required")
    try:
        status = simulator.status(cp_id)
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Simulator status failed")
        return _json_error(str(exc))
    return jsonify(_serialize_status(status)), HTTPStatus.OK
