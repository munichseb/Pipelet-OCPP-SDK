"""Structured logging helper."""

DEFAULT_NAME = "Structured Logger"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Schreibt strukturierte Logeinträge in den Kontext (__log)." 

CODE = '''
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
'''
