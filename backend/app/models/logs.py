"""Run log model definition."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class RunLog(db.Model):
    """Represents log entries for workflow and pipelet executions."""

    __tablename__ = "run_logs"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(
        db.Enum("cp", "cs", "pipelet", name="runlog_source"), nullable=False
    )
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr not critical for tests
        return f"<RunLog {self.id} from {self.source}>"
