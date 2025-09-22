"""Async OCPP central system server implementation."""

from __future__ import annotations

import asyncio
import itertools
import threading
from datetime import UTC, datetime

import websockets
from flask import Flask
from ocpp.routing import on
from ocpp.v16 import ChargePoint as OcppChargePoint
from ocpp.v16 import call_result
from ocpp.v16.datatypes import IdTagInfo
from ocpp.v16.enums import Action, AuthorizationStatus, RegistrationStatus
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from ..workflow.runner import run_workflow_for_event
from .logging import persist_run_log

OCPP_SUBPROTOCOL = "ocpp1.6"


class LoggingWebSocket:
    """Proxy object around a websocket connection to persist raw frames."""

    def __init__(self, websocket: WebSocketServerProtocol, app: Flask, source: str):
        self._websocket = websocket
        self._app = app
        self._source = source

    async def send(self, message: str) -> None:
        persist_run_log(self._app, self._source, f"send: {message}")
        await self._websocket.send(message)

    async def recv(self) -> str:
        message = await self._websocket.recv()
        persist_run_log(self._app, self._source, f"recv: {message}")
        return message

    async def close(self, *args, **kwargs) -> None:  # pragma: no cover - passthrough
        await self._websocket.close(*args, **kwargs)

    def __getattr__(self, item: str) -> object:  # pragma: no cover - passthrough
        return getattr(self._websocket, item)


class CentralSystemChargePoint(OcppChargePoint):
    """Charge point handler hosted by the central system."""

    def __init__(
        self,
        cp_id: str,
        connection: LoggingWebSocket,
        server: CentralSystemServer,
    ) -> None:
        super().__init__(cp_id, connection)
        self._server = server

    async def start(self) -> None:  # pragma: no cover - exercised via integration tests
        while True:
            try:
                message = await self._connection.recv()
            except ConnectionClosed:
                break
            try:
                await self.route_message(message)
            except Exception as exc:  # pragma: no cover - defensive logging
                persist_run_log(
                    self._server.app,
                    "cs",
                    f"error handling message from {self.id}: {exc}",
                )
        # Connection closed is logged by the server after the handler exits.

    def _execute_workflow(self, event: str, payload: dict[str, object]) -> None:
        try:
            with self._server.app.app_context():
                run_workflow_for_event(
                    event,
                    dict(payload),
                    {"cp_id": self.id, "event": event},
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            persist_run_log(
                self._server.app,
                "cs",
                f"workflow execution for event {event} failed: {exc}",
            )

    async def _trigger_workflow(self, event: str, payload: dict[str, object]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._execute_workflow, event, payload)

    @on(Action.boot_notification)
    async def on_boot_notification(  # type: ignore[override]
        self,
        charge_point_model: str,
        charge_point_vendor: str,
        **payload: object,
    ) -> call_result.BootNotification:
        message = {
            "charge_point_model": charge_point_model,
            "charge_point_vendor": charge_point_vendor,
            **payload,
        }
        await self._trigger_workflow("BootNotification", message)
        current_time = datetime.now(UTC).isoformat()
        return call_result.BootNotification(
            current_time=current_time,
            interval=10,
            status=RegistrationStatus.accepted,
        )

    @on(Action.heartbeat)
    async def on_heartbeat(self) -> call_result.Heartbeat:  # type: ignore[override]
        await self._trigger_workflow("Heartbeat", {})
        current_time = datetime.now(UTC).isoformat()
        return call_result.Heartbeat(current_time=current_time)

    @on(Action.authorize)
    async def on_authorize(  # type: ignore[override]
        self, id_tag: str
    ) -> call_result.Authorize:
        await self._trigger_workflow("Authorize", {"id_tag": id_tag})
        id_tag_info = IdTagInfo(status=AuthorizationStatus.accepted)
        return call_result.Authorize(id_tag_info=id_tag_info)

    @on(Action.start_transaction)
    async def on_start_transaction(  # type: ignore[override]
        self,
        connector_id: int,
        id_tag: str,
        meter_start: int,
        timestamp: str,
        **payload: object,
    ) -> call_result.StartTransaction:
        message = {
            "connector_id": connector_id,
            "id_tag": id_tag,
            "meter_start": meter_start,
            "timestamp": timestamp,
            **payload,
        }
        await self._trigger_workflow("StartTransaction", message)
        transaction_id = self._server.next_transaction_id()
        id_tag_info = IdTagInfo(status=AuthorizationStatus.accepted)
        return call_result.StartTransaction(
            transaction_id=transaction_id,
            id_tag_info=id_tag_info,
        )

    @on(Action.stop_transaction)
    async def on_stop_transaction(  # type: ignore[override]
        self,
        meter_stop: int,
        timestamp: str,
        transaction_id: int,
        **payload: object,
    ) -> call_result.StopTransaction:
        message = {
            "meter_stop": meter_stop,
            "timestamp": timestamp,
            "transaction_id": transaction_id,
            **payload,
        }
        await self._trigger_workflow("StopTransaction", message)
        id_tag_info = IdTagInfo(status=AuthorizationStatus.accepted)
        return call_result.StopTransaction(id_tag_info=id_tag_info)


class CentralSystemServer:
    """Manages the OCPP central system server lifecycle."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._transaction_ids = itertools.count(1)
        self._server: websockets.server.Serve | None = None

    def start(self) -> None:
        if self._thread.is_alive():
            return
        self._thread.start()
        future = asyncio.run_coroutine_threadsafe(self._start_server(), self._loop)
        future.result(timeout=5)

    def next_transaction_id(self) -> int:
        return next(self._transaction_ids)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _start_server(self) -> None:
        self._server = await websockets.serve(
            self._on_connect,
            host="0.0.0.0",
            port=9000,
            subprotocols=[OCPP_SUBPROTOCOL],
        )

    async def _on_connect(self, websocket: WebSocketServerProtocol, path: str) -> None:
        cp_id = _extract_cp_id(path)
        if cp_id is None:
            await websocket.close(code=4000, reason="Invalid charge point id")
            return
        logging_ws = LoggingWebSocket(websocket, self.app, "cs")
        persist_run_log(self.app, "cs", f"connection established with {cp_id}")
        charge_point = CentralSystemChargePoint(cp_id, logging_ws, self)
        try:
            await charge_point.start()
        finally:
            persist_run_log(self.app, "cs", f"connection closed with {cp_id}")


_server_instance: CentralSystemServer | None = None
_server_lock = threading.Lock()


def ensure_server_started(app: Flask) -> CentralSystemServer:
    """Ensure the central system server is running for the given Flask app."""
    global _server_instance
    with _server_lock:
        if _server_instance is None:
            _server_instance = CentralSystemServer(app)
            _server_instance.start()
    return _server_instance


def _extract_cp_id(path: str) -> str | None:
    if not path:
        return None
    # Expected format: /CP_<id>
    candidate = path.strip("/")
    if not candidate.startswith("CP_"):
        return None
    return candidate
