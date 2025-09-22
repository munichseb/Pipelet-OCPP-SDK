"""Health check endpoint."""

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.get("/health")
def health() -> tuple[dict[str, str], int]:
    """Return the service health status."""
    return jsonify({"status": "ok"}), 200
