"""Simple debugging template pipelet."""

DEFAULT_NAME = "Debug Template"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Setzt ein Debug-Feld mit der Chargepoint-ID." 

CODE = '''
from copy import deepcopy

def run(message, context):
    """Return an augmented copy of the incoming message for debugging."""

    data = deepcopy(message or {})
    data["_debug"] = f"cp={context.get('cp_id', 'unknown')}"
    return data
'''
