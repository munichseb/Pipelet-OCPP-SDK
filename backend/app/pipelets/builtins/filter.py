"""Conditional filtering pipelet."""

DEFAULT_NAME = "Event Filter"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Lässt nur StartTransaction-Ereignisse durch und dropt andere." 

CODE = '''
def run(message, context):
    """Allow only StartTransaction events to pass through."""

    if context.get("event") != "StartTransaction":
        return None
    return message
'''
