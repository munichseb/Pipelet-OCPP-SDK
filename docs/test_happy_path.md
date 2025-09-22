Test the complete flow on a mac:

#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:5000"

echo "1) Healthcheck..."
curl -s $BASE/api/health | jq .

echo "2) Connect CP_1 (inkl. BootNotification)..."
curl -s -X POST $BASE/api/sim/connect -H "Content-Type: application/json" \
     -d '{"cp_id": "CP_1"}' | jq .

sleep 2

echo "3) Start Heartbeats..."
curl -s -X POST $BASE/api/sim/heartbeat/start -H "Content-Type: application/json" \
     -d '{"cp_id": "CP_1"}' | jq .

sleep 2

echo "4) RFID vorhalten (Tag=ABC123)..."
curl -s -X POST $BASE/api/sim/rfid -H "Content-Type: application/json" \
     -d '{"cp_id": "CP_1", "idTag": "ABC123"}' | jq .

echo "5) StartTransaction (Tag=ABC123)..."
curl -s
