"""WSGI entry point for the Pipelet OCPP backend."""

from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":  # pragma: no cover - manual runtime entrypoint
    port_env = os.getenv("PIPELET_API_PORT") or os.getenv("PORT")
    port = int(port_env) if port_env else 9200
    app.run(host="0.0.0.0", port=port)
