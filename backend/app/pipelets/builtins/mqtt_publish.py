"""MQTT publish placeholder pipelet."""

DEFAULT_NAME = "MQTT Publish (Stub)"
DEFAULT_EVENT = "StartTransaction"
DESCRIPTION = "Demonstriert die Übergabe an MQTT – derzeit nur Logging im Kontext." 

CODE = '''
def run(message, context):
    """Simulate publishing the message to an MQTT topic."""

    topic = context.get("mqtt_topic", "ocpp/pipelet")
    entries = context.setdefault("__log", [])
    entries.append({
        "level": "info",
        "message": f"MQTT publish to {topic} (stub)",
    })
    return message
'''
