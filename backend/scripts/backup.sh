#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE=".env"
OUTPUT_FILE=""

usage() {
  cat <<USAGE
Usage: backend/scripts/backup.sh [--output FILE] [--env FILE]

Create a MySQL dump using credentials from DATABASE_URL.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--env)
      ENV_FILE="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

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

BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEFAULT_OUTPUT="$BACKUP_DIR/pipelet_${TIMESTAMP}.sql"
BACKUP_FILE="${OUTPUT_FILE:-$DEFAULT_OUTPUT}"

echo "Creating backup at $BACKUP_FILE"
docker compose exec db mysqldump \
  -u"$DB_USER" --password="$DB_PASSWORD" \
  "$DB_NAME" > "$BACKUP_FILE"

echo "Backup completed"
