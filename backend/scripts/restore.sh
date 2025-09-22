#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE=".env"
INPUT_FILE=""

usage() {
  cat <<USAGE
Usage: backend/scripts/restore.sh [--env FILE] --file DUMP.sql

Restore a MySQL dump produced by backend/scripts/backup.sh.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--env)
      ENV_FILE="$2"
      shift 2
      ;;
    -f|--file)
      INPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$INPUT_FILE" && -f "$1" ]]; then
        INPUT_FILE="$1"
        shift 1
      else
        echo "Unknown argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$INPUT_FILE" ]]; then
  echo "Missing dump file. Provide --file <dump.sql>." >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Dump file '$INPUT_FILE' not found" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
elif [[ "$ENV_FILE" != ".env" ]]; then
  echo "Environment file '$ENV_FILE' not found" >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not defined" >&2
  exit 1
fi

mapfile -t DB_PARTS < <(python - <<'PY'
import os
from urllib.parse import urlparse

url = urlparse(os.environ["DATABASE_URL"])
print(url.username or "")
print(url.password or "")
print((url.path or "/").lstrip("/"))
PY
)

DB_USER="${DB_PARTS[0]}"
DB_PASSWORD="${DB_PARTS[1]}"
DB_NAME="${DB_PARTS[2]}"

echo "Restoring $INPUT_FILE into $DB_NAME"
docker compose exec -T db mysql \
  -u"$DB_USER" --password="$DB_PASSWORD" \
  "$DB_NAME" < "$INPUT_FILE"

echo "Restore completed"
