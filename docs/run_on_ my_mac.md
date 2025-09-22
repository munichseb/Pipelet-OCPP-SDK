Hier ist eine kurze, pragmatische Test-Checkliste (Docker-Variante zuerst, dann „native“ Dev-Variante) um die Lösung auf einem Mac lokal laufen zu lassen:

# Quickstart

Voraussetzungen

Docker Desktop für macOS (Ports 9200, 5173, 9000, 3306 frei).

Repository klonen & .env setzen

git clone https://github.com/munichseb/Pipelet-OCPP-SDK.git
cd Pipelet-OCPP-SDK
cp .env.example .env


Stack starten (MySQL + Backend + Frontend)

docker compose up --build


Danach sollten Backend & Frontend unter diesen URLs erreichbar sein (stehen auch im README):

Backend API: http://localhost:9200

Frontend (Workflow-Canvas + Simulator): http://localhost:5173
 
GitHub

Seed-Daten einspielen (Built-in-Pipelets + Beispiel-Workflow)

# neues Terminal
docker compose exec backend python backend/scripts/seed.py


Das legt u.a. den Demo-Workflow Debug Template -> Start Meter Transformer -> HTTP Webhook an und bindet ihn an StartTransaction. Der Seed ist idempotent. 
GitHub

Smoke-Tests

Healthcheck:

curl http://localhost:9200/api/health


Erwartet: {"status":"ok"}.

Frontend öffnen: http://localhost:5173

Dort findest du:

Simulator-Panel (CP-ID wählen, Connect/Disconnect, RFID senden, Start/Stop, Heartbeat toggle),

Statusleisten (CS WebSocket auf :9000, CP-Verbindung),

Live-Logs (SSE-Stream, Suche, Auto-Scroll, Download). 
GitHub

Simulator bedienen (im Frontend)

Connect klicken ⇒ es sollte automatisch eine BootNotification gesendet/akzeptiert werden und danach periodische Heartbeats (Intervall aus der Conf).

RFID vorhalten (eine ID eingeben) ⇒ Authorize (immer Accepted).

Start ⇒ StartTransaction (transactionId wird vergeben).

Stop ⇒ StopTransaction.
Alle Frames siehst du live im Log-Viewer; zusätzlich kannst du einen NDJSON-Snapshot via „Download“ holen (nutzt /api/logs/download). 
GitHub

Export/Import ausprobieren (optional)

Export:

curl http://localhost:9200/api/export -o export.json


Import (z.B. in frischer DB):

curl -X POST -H "Content-Type: application/json" \
     --data @export.json "http://localhost:9200/api/import?overwrite=true"


Struktur steht im README.
