"""OCPP 1.6J charge point simulator."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, datetime

import websockets
from flask import Flask
from ocpp.v16 import ChargePoint as OcppChargePoint
from ocpp.v16 import call
from websockets.exceptions import ConnectionClosed

from .logging import persist_run_log
from .server import OCPP_SUBPROTOCOL, LoggingWebSocket


@dataclass
class SimulatorState:
    """State snapshot returned to REST handlers."""

    interval: int
    transaction_id: int | None


class SimulatorChargePoint(OcppChargePoint):
    """Charge point implementation for the simulator."""

    def __init__(self, cp_id: str, connection: LoggingWebSocket, simulator: ChargePointSimulator) -> None:
        super().__init__(cp_id, connection)
        self._simulator = simulator

    async def start(self) -> None:  # pragma: no cover - exercised through integration
        while True:
            try:
                message = await self._connection.recv()
            except ConnectionClosed:
                break
            try:
                await self.route_message(message)
            except Exception as exc:  # pragma: no cover - defensive logging
                persist_run_log(
                    self._simulator.app,
                    "cp",
                    f"error handling message for {self.id}: {exc}",
                )

    async def send_boot_notification(self) -> object:
        request = call.BootNotification(
            charge_point_model="Simulator",
            charge_point_vendor="Pipelet",
        )
        return await self.call(request)

    async def send_heartbeat(self) -> object:
        request = call.Heartbeat()
        return await self.call(request)

    async def send_authorize(self, id_tag: str) -> object:
        request = call.Authorize(id_tag=id_tag)
        return await self.call(request)

    async def send_start_transaction(self, id_tag: str) -> object:
        request = call.StartTransaction(
            connector_id=1,
            id_tag=id_tag,
            meter_start=0,
            timestamp=datetime.now(UTC).isoformat(),
        )
        return await self.call(request)

    async def send_stop_transaction(self, transaction_id: int, id_tag: str | None = None) -> object:
        request = call.StopTransaction(
            meter_stop=10,
            timestamp=datetime.now(UTC).isoformat(),
            transaction_id=transaction_id,
            id_tag=id_tag,
        )
        return await self.call(request)


class ChargePointSimulator:
    """Manage simulator lifecycle and expose synchronous helpers for REST handlers."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._connection: LoggingWebSocket | None = None
        self._charge_point: SimulatorChargePoint | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._interval: int = 10
        self._active_transaction_id: int | None = None

    def connect(self) -> SimulatorState:
        return self._sync(self._connect())

    def start_heartbeat(self) -> SimulatorState:
        return self._sync(self._start_heartbeat())

    def authorize(self, id_tag: str) -> SimulatorState:
        return self._sync(self._authorize(id_tag))

    def start_transaction(self, id_tag: str) -> SimulatorState:
        return self._sync(self._start_transaction(id_tag))

    def stop_transaction(self) -> SimulatorState:
        return self._sync(self._stop_transaction())

    def _sync(self, coro: Awaitable[SimulatorState]) -> SimulatorState:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        result = future.result(timeout=10)
        return result

    async def _connect(self) -> SimulatorState:
        if self._charge_point is None:
            websocket = await websockets.connect(
                "ws://localhost:9000/CP_1",
                subprotocols=[OCPP_SUBPROTOCOL],
            )
            logging_ws = LoggingWebSocket(websocket, self.app, "cp")
            self._connection = logging_ws
            self._charge_point = SimulatorChargePoint("CP_1", logging_ws, self)
            self._receiver_task = asyncio.create_task(self._charge_point.start())
            response = await self._charge_point.send_boot_notification()
            interval = getattr(response, "interval", 10)
            self._interval = int(interval)
        return SimulatorState(interval=self._interval, transaction_id=self._active_transaction_id)

    async def _start_heartbeat(self) -> SimulatorState:
        await self._ensure_connected()
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        return SimulatorState(interval=self._interval, transaction_id=self._active_transaction_id)

    async def _authorize(self, id_tag: str) -> SimulatorState:
        await self._ensure_connected()
        await self._charge_point.send_authorize(id_tag)
        return SimulatorState(interval=self._interval, transaction_id=self._active_transaction_id)

    async def _start_transaction(self, id_tag: str) -> SimulatorState:
        await self._ensure_connected()
        response = await self._charge_point.send_start_transaction(id_tag)
        transaction_id = getattr(response, "transaction_id", None)
        if transaction_id is not None:
            self._active_transaction_id = int(transaction_id)
        return SimulatorState(interval=self._interval, transaction_id=self._active_transaction_id)

    async def _stop_transaction(self) -> SimulatorState:
        await self._ensure_connected()
        if self._active_transaction_id is None:
            raise RuntimeError("No active transaction")
        await self._charge_point.send_stop_transaction(self._active_transaction_id)
        self._active_transaction_id = None
        return SimulatorState(interval=self._interval, transaction_id=None)

    async def _ensure_connected(self) -> None:
        if self._charge_point is None:
            await self._connect()

    async def _heartbeat_loop(self) -> None:  # pragma: no cover - requires integration
        while True:
            try:
                await self._charge_point.send_heartbeat()
            except Exception as exc:  # pragma: no cover - defensive logging
                persist_run_log(
                    self.app,
                    "cp",
                    f"heartbeat failed: {exc}",
                )
            await asyncio.sleep(self._interval)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()


def get_simulator(app: Flask) -> ChargePointSimulator:
    """Return a singleton simulator tied to the Flask app."""
    if "cp_simulator" not in app.extensions:
        app.extensions["cp_simulator"] = ChargePointSimulator(app)
    return app.extensions["cp_simulator"]
