"""WSGI entry point for the Pipelet OCPP backend."""

from app import create_app

app = create_app()
