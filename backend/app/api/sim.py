"""REST triggers for the OCPP charge point simulator."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request

from ..ocpp.simulator import SimulatorState, get_simulator

bp = Blueprint("sim", __name__)


def _serialize_state(state: SimulatorState) -> dict[str, object]:
    return {
        "interval": state.interval,
        "transactionId": state.transaction_id,
    }


def _json_error(message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
    return jsonify({"error": message}), status


@bp.post("/sim/connect")
def connect() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        state = simulator.connect()
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Simulator connect failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/heartbeat/start")
def start_heartbeat() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        state = simulator.start_heartbeat()
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Heartbeat start failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


def _require_id_tag() -> str:
    payload = request.get_json(silent=True) or {}
    id_tag = payload.get("idTag")
    if not isinstance(id_tag, str) or not id_tag:
        raise ValueError("idTag is required")
    return id_tag


@bp.post("/sim/rfid")
def authorize() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        id_tag = _require_id_tag()
        state = simulator.authorize(id_tag)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Authorize failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/start")
def start_transaction() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        id_tag = _require_id_tag()
        state = simulator.start_transaction(id_tag)
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Start transaction failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK


@bp.post("/sim/stop")
def stop_transaction() -> tuple[object, int]:
    simulator = get_simulator(current_app)
    try:
        state = simulator.stop_transaction()
    except Exception as exc:  # pragma: no cover - defensive branch
        current_app.logger.exception("Stop transaction failed")
        return _json_error(str(exc))
    return jsonify(_serialize_state(state)), HTTPStatus.OK
