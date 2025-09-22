"""Compatibility package that exposes the backend Flask application factory."""

from backend.app import Config, create_app

__all__ = ["Config", "create_app"]
