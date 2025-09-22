"""Application factory for the Pipelet OCPP backend."""

from flask import Flask

from .api.health import bp as health_bp
from .api.logs import bp as logs_bp
from .api.sim import bp as sim_bp
from .config import Config
from .extensions import cors, db
from .ocpp.server import ensure_server_started


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    if cors is not None:
        cors.init_app(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(logs_bp, url_prefix="/api")
    app.register_blueprint(sim_bp, url_prefix="/api")

    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy before creating tables.
        from .models import logs, pipelet, workflow  # noqa: F401

        db.create_all()

    ensure_server_started(app)

    return app
