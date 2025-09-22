"""Routing helper to decide downstream targets."""

DEFAULT_NAME = "Routing Decision"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Leitet die Nachricht je nach CP-ID an unterschiedliche Ziele weiter." 

CODE = '''
def run(message, context):
    """Decide on a routing target and store it in the context."""

    cp_id = context.get("cp_id", "unknown")
    if isinstance(cp_id, str) and cp_id.endswith("1"):
        target = "A"
    else:
        target = "B"
    context.setdefault("route_to", {})["cpms"] = target
    return message
'''
