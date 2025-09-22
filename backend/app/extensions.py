"""Extensions used by the Flask application."""

from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
cors = CORS()

__all__ = ["db", "cors"]
