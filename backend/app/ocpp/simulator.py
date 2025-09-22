"""OCPP 1.6J charge point simulator."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, TypeVar

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


@dataclass
class SimulatorStatus:
    """Status information exposed through the REST API."""

    connected: bool
    last_event_ts: datetime | None


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


T = TypeVar("T")


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

        self._cp_id: str | None = None
        self._last_cp_id: str | None = None
        self._last_event: datetime | None = None

    def connect(self, cp_id: str) -> SimulatorState:
        return self._sync(self._connect(cp_id))

    def disconnect(self) -> SimulatorState:
        return self._sync(self._disconnect())

    def start_heartbeat(self, cp_id: str) -> SimulatorState:
        return self._sync(self._start_heartbeat(cp_id))

    def stop_heartbeat(self, cp_id: str) -> SimulatorState:
        return self._sync(self._stop_heartbeat(cp_id))

    def authorize(self, cp_id: str, id_tag: str) -> SimulatorState:
        return self._sync(self._authorize(cp_id, id_tag))

    def start_transaction(self, cp_id: str, id_tag: str) -> SimulatorState:
        return self._sync(self._start_transaction(cp_id, id_tag))

    def stop_transaction(self, cp_id: str) -> SimulatorState:
        return self._sync(self._stop_transaction(cp_id))

    def status(self, cp_id: str) -> SimulatorStatus:
        return self._sync(self._status(cp_id))

    def _sync(self, coro: Awaitable[T]) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        result = future.result(timeout=10)
        return result

    async def _connect(self, cp_id: str) -> SimulatorState:
        if self._charge_point is None or self._cp_id != cp_id:
            if self._charge_point is not None and self._cp_id != cp_id:
                await self._disconnect_internal()
            websocket = await websockets.connect(
                f"ws://localhost:9000/{cp_id}",
                subprotocols=[OCPP_SUBPROTOCOL],
            )
            logging_ws = LoggingWebSocket(websocket, self.app, "cp")
            self._connection = logging_ws
            self._charge_point = SimulatorChargePoint(cp_id, logging_ws, self)
            self._receiver_task = asyncio.create_task(self._charge_point.start())
            self._cp_id = cp_id
            self._last_cp_id = cp_id

        response = await self._charge_point.send_boot_notification()
        interval = getattr(response, "interval", 10)
        self._interval = int(interval)
        self._mark_event()
        return SimulatorState(
            interval=self._interval,
            transaction_id=self._active_transaction_id,
        )

    async def _disconnect(self) -> SimulatorState:
        await self._disconnect_internal()
        self._mark_event()
        return SimulatorState(interval=self._interval, transaction_id=None)

    async def _start_heartbeat(self, cp_id: str) -> SimulatorState:
        await self._ensure_connected(cp_id)
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._mark_event()
        return SimulatorState(
            interval=self._interval,
            transaction_id=self._active_transaction_id,
        )

    async def _stop_heartbeat(self, cp_id: str) -> SimulatorState:
        await self._ensure_connected(cp_id)
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                pass
            self._heartbeat_task = None
        self._mark_event()
        return SimulatorState(
            interval=self._interval,
            transaction_id=self._active_transaction_id,
        )

    async def _authorize(self, cp_id: str, id_tag: str) -> SimulatorState:
        await self._ensure_connected(cp_id)
        await self._charge_point.send_authorize(id_tag)
        self._mark_event()
        return SimulatorState(
            interval=self._interval,
            transaction_id=self._active_transaction_id,
        )

    async def _start_transaction(self, cp_id: str, id_tag: str) -> SimulatorState:
        await self._ensure_connected(cp_id)
        response = await self._charge_point.send_start_transaction(id_tag)
        transaction_id = getattr(response, "transaction_id", None)
        if transaction_id is not None:
            self._active_transaction_id = int(transaction_id)
        self._mark_event()
        return SimulatorState(
            interval=self._interval,
            transaction_id=self._active_transaction_id,
        )

    async def _stop_transaction(self, cp_id: str) -> SimulatorState:
        await self._ensure_connected(cp_id)
        if self._active_transaction_id is None:
            raise RuntimeError("No active transaction")
        await self._charge_point.send_stop_transaction(self._active_transaction_id)
        self._active_transaction_id = None
        self._mark_event()
        return SimulatorState(interval=self._interval, transaction_id=None)

    async def _status(self, cp_id: str) -> SimulatorStatus:
        connected = self._charge_point is not None and self._cp_id == cp_id
        last_event_ts = self._last_event if self._last_cp_id == cp_id else None
        return SimulatorStatus(connected=connected, last_event_ts=last_event_ts)

    async def _ensure_connected(self, cp_id: str) -> None:
        if self._charge_point is None or self._cp_id != cp_id:
            raise RuntimeError("Simulator is not connected to the requested charge point")

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
                self._mark_event()
            await asyncio.sleep(self._interval)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _disconnect_internal(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                pass
            self._heartbeat_task = None

        if self._receiver_task is not None:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                pass
            self._receiver_task = None

        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:  # pragma: no cover - defensive close helper
                persist_run_log(
                    self.app,
                    "cp",
                    "failed to close simulator connection cleanly",
                )

        previous_cp = self._cp_id
        self._connection = None
        self._charge_point = None
        self._cp_id = None
        if previous_cp is not None:
            self._last_cp_id = previous_cp
        self._active_transaction_id = None

    def _mark_event(self) -> None:
        self._last_event = datetime.now(UTC)


def get_simulator(app: Flask) -> ChargePointSimulator:
    """Return a singleton simulator tied to the Flask app."""
    if "cp_simulator" not in app.extensions:
        app.extensions["cp_simulator"] = ChargePointSimulator(app)
    return app.extensions["cp_simulator"]
