export interface SeedPipelet {
  name: string
  event: string
  code: string
}

export interface SeedWorkflow {
  name: string
  event: string | null
  graph_json: string
}

export interface SeedPayload {
  pipelets: SeedPipelet[]
  workflows: SeedWorkflow[]
}

function normalizeCode(code: string): string {
  return `${code.replace(/^[\n]+|[\n]+$/g, '')}\n`
}

const BUILTIN_PIPELETS: SeedPipelet[] = [
  {
    name: 'Debug Template',
    event: 'StartTransaction',
    code: normalizeCode(`
from copy import deepcopy

def run(message, context):
    """Return an augmented copy of the incoming message for debugging."""

    data = deepcopy(message or {})
    data["_debug"] = f"cp={context.get('cp_id', 'unknown')}"
    return data
    `),
  },
  {
    name: 'Start Meter Transformer',
    event: 'StartTransaction',
    code: normalizeCode(`
def run(message, context):
    """Rename and enrich fields in the payload."""

    result = dict(message or {})
    if "meterStart" in result:
        result["meter_start"] = result.pop("meterStart")
    result.setdefault("source", "ocpp")
    return result
    `),
  },
  {
    name: 'Event Filter',
    event: 'StartTransaction',
    code: normalizeCode(`
def run(message, context):
    """Allow only StartTransaction events to pass through."""

    if context.get("event") != "StartTransaction":
        return None
    return message
    `),
  },
  {
    name: 'Routing Decision',
    event: 'StartTransaction',
    code: normalizeCode(`
def run(message, context):
    """Decide on a routing target and store it in the context."""

    cp_id = context.get("cp_id", "unknown")
    if isinstance(cp_id, str) and cp_id.endswith("1"):
        target = "A"
    else:
        target = "B"
    context.setdefault("route_to", {})["cpms"] = target
    return message
    `),
  },
  {
    name: 'HTTP Webhook',
    event: 'StartTransaction',
    code: normalizeCode(`
from typing import Any

import requests


def run(message, context):
    """Send the payload to a configured webhook URL and continue the flow."""

    url = context.get("webhook_url")
    if not url:
        return message

    payload: Any = message if isinstance(message, (dict, list)) else {"data": message}
    try:
        requests.post(url, json=payload, timeout=1.0)
    except Exception as exc:  # pragma: no cover - network issues not deterministic
        context["webhook_error"] = str(exc)
    return message
    `),
  },
  {
    name: 'MQTT Publish (Stub)',
    event: 'StartTransaction',
    code: normalizeCode(`
def run(message, context):
    """Simulate publishing the message to an MQTT topic."""

    topic = context.get("mqtt_topic", "ocpp/pipelet")
    entries = context.setdefault("__log", [])
    entries.append({
        "level": "info",
        "message": f"MQTT publish to {topic} (stub)",
    })
    return message
    `),
  },
  {
    name: 'Structured Logger',
    event: 'StartTransaction',
    code: normalizeCode(`
from datetime import datetime

def run(message, context):
    """Append a structured log entry to the context."""

    entries = context.setdefault("__log", [])
    entries.append(
        {
            "level": "info",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": "Pipelet executed",
        }
    )
    return message
    `),
  },
]

const EXAMPLE_PIPELET_NAMES = [
  'Debug Template',
  'Start Meter Transformer',
  'HTTP Webhook',
]

// Must match the editor identifier used in WorkflowCanvas
const WORKFLOW_EDITOR_ID = 'pipelet-workflow@0.1.0'

function buildExampleWorkflowGraph(pipelets: SeedPipelet[]): string {
  const nodes: Record<string, unknown> = {}
  pipelets.forEach((pipelet, index) => {
    const id = index + 1
    const isLast = index === pipelets.length - 1
    nodes[String(id)] = {
      id,
      data: {
        code: pipelet.code,
        pipelet: { name: pipelet.name },
      },
      outputs: isLast
        ? {}
        : {
            out: {
              connections: [
                {
                  node: id + 1,
                },
              ],
            },
          },
    }
  })
  return JSON.stringify({
    id: WORKFLOW_EDITOR_ID,
    nodes,
  })
}

export function createSeedPayload(): SeedPayload {
  const pipelets = BUILTIN_PIPELETS.map((pipelet) => ({ ...pipelet }))
  const workflowPipelets = EXAMPLE_PIPELET_NAMES.map((name) => {
    const match = BUILTIN_PIPELETS.find((pipelet) => pipelet.name === name)
    if (!match) {
      throw new Error(`Missing built-in pipelet definition for ${name}`)
    }
    return match
  })

  return {
    pipelets,
    workflows: [
      {
        name: 'StartTransaction Flow',
        event: 'StartTransaction',
        graph_json: buildExampleWorkflowGraph(workflowPipelets),
      },
    ],
  }
}
