"""HTTP webhook integration pipelet."""

DEFAULT_NAME = "HTTP Webhook"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Sendet das Ergebnis per HTTP POST an eine konfigurierbare URL." 

CODE = '''
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
'''
