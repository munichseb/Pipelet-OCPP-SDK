"""Application factory for the Pipelet OCPP backend."""
from __future__ import annotations

import time

from flask import Flask
from sqlalchemy.exc import OperationalError

from .config import Config
from .extensions import cors, db, limiter


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    if cors is not None:
        allowed_origins = [
            origin.strip()
            for origin in (app.config.get("CORS_ALLOWED_ORIGINS") or "").split(",")
            if origin.strip()
        ]
        cors.init_app(
            app,
            resources={r"/api/*": {"origins": allowed_origins}},
            allow_headers=["Content-Type", "Authorization"],
        )

    limiter.init_app(app)

    from .api.auth import bp as auth_bp
    from .api.export import bp as export_bp
    from .api.health import bp as health_bp
    from .api.logs import bp as logs_bp
    from .api.pipelets import bp as pipelets_bp
    from .api.workflow import bp as workflow_bp

    sim_bp = None
    if app.config.get("ENABLE_SIM_API", True):
        from .api.sim import bp as sim_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(logs_bp, url_prefix="/api")
    if sim_bp is not None:
        app.register_blueprint(sim_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")
    app.register_blueprint(pipelets_bp, url_prefix="/api")
    app.register_blueprint(workflow_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")

    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy before creating tables.
        from .models import auth, logs, pipelet, settings, workflow  # noqa: F401

        _initialize_database(app)

    if app.config.get("ENABLE_OCPP_SERVER", True):
        from .ocpp.server import ensure_server_started

        ensure_server_started(app)

    return app


def _initialize_database(app: Flask) -> None:
    """Initialize the database with retry logic to handle delayed availability."""

    max_retries = int(app.config.get("DB_INIT_MAX_RETRIES", 30))
    retry_delay = float(app.config.get("DB_INIT_RETRY_DELAY", 2))

    for attempt in range(1, max_retries + 1):
        try:
            db.create_all()
            return
        except OperationalError as exc:
            if attempt >= max_retries:
                app.logger.exception("Database initialization failed after %s attempts.", attempt)
                raise

            app.logger.warning(
                "Database initialization attempt %s/%s failed: %s", attempt, max_retries, exc
            )
            time.sleep(retry_delay)

