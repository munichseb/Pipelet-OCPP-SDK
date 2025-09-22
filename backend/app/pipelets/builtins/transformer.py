"""Message transformation helper."""

DEFAULT_NAME = "Start Meter Transformer"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Benennt meterStart in meter_start um und ergänzt source=ocpp." 

CODE = '''
def run(message, context):
    """Rename and enrich fields in the payload."""

    result = dict(message or {})
    if "meterStart" in result:
        result["meter_start"] = result.pop("meterStart")
    result.setdefault("source", "ocpp")
    return result
'''
