"""Seed the database with built-in pipelets and an example workflow."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.pipelet import Pipelet
from backend.app.models.workflow import Workflow
from backend.app.pipelets.builtins import (
    BuiltinPipelet,
    find_builtin,
    iter_builtin_pipelets,
)

EXAMPLE_WORKFLOW_NAME = "StartTransaction Flow"
EXAMPLE_EVENT = "StartTransaction"


def _ensure_pipelet(builtin: BuiltinPipelet) -> tuple[bool, bool]:
    """Create or update a pipelet from the built-in definition."""

    created = False
    updated = False

    pipelet = Pipelet.query.filter_by(name=builtin.name).first()
    if pipelet is None:
        pipelet = Pipelet(name=builtin.name, event=builtin.event, code=builtin.code)
        db.session.add(pipelet)
        created = True
    else:
        if pipelet.event != builtin.event or pipelet.code != builtin.code:
            pipelet.event = builtin.event
            pipelet.code = builtin.code
            updated = True
    return created, updated


def _chain_graph(pipelets: Iterable[BuiltinPipelet]) -> str:
    """Build a simple linear workflow graph for the provided pipelets."""

    nodes: dict[str, object] = {}
    items = list(pipelets)
    for index, builtin in enumerate(items, start=1):
        outputs = {}
        if index < len(items):
            outputs = {"out": {"connections": [{"node": index + 1}]}}
        nodes[str(index)] = {
            "id": index,
            "data": {
                "code": builtin.code,
                "pipelet": {"name": builtin.name},
            },
            "outputs": outputs,
        }
    return json.dumps({"nodes": nodes})


def _ensure_example_workflow(pipelets: Iterable[BuiltinPipelet]) -> tuple[bool, bool]:
    graph_json = _chain_graph(pipelets)
    workflow = Workflow.query.filter_by(name=EXAMPLE_WORKFLOW_NAME).first()
    created = False
    updated = False

    if workflow is None:
        workflow = Workflow(
            name=EXAMPLE_WORKFLOW_NAME,
            event=EXAMPLE_EVENT,
            graph_json=graph_json,
        )
        db.session.add(workflow)
        created = True
    else:
        if workflow.event != EXAMPLE_EVENT or workflow.graph_json != graph_json:
            workflow.event = EXAMPLE_EVENT
            workflow.graph_json = graph_json
            updated = True
    return created, updated


def main() -> None:
    app = create_app()
    with app.app_context():
        created_pipelets = 0
        updated_pipelets = 0
        for builtin in iter_builtin_pipelets():
            created, updated = _ensure_pipelet(builtin)
            created_pipelets += int(created)
            updated_pipelets += int(updated)

        template = find_builtin("Debug Template")
        transformer = find_builtin("Start Meter Transformer")
        webhook = find_builtin("HTTP Webhook")
        if template is None or transformer is None or webhook is None:
            raise RuntimeError("Missing built-in definitions for example workflow")

        created_workflows, updated_workflows = _ensure_example_workflow(
            [template, transformer, webhook]
        )

        db.session.commit()

        print(
            "Seed completed",
            f"pipelets created={created_pipelets}",
            f"pipelets updated={updated_pipelets}",
            f"workflows created={int(created_workflows)}",
            f"workflows updated={int(updated_workflows)}",
        )


if __name__ == "__main__":
    main()
