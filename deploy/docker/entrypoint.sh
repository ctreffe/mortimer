#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[$(date +"%Y-%m-%dT%H:%M:%S%z")] $*"
}

REQUIRED_VARS=(
  "MORTIMER_SECRET_KEY"
  "MORTIMER_MONGO_HOST"
  "MORTIMER_MONGO_PORT"
  "MORTIMER_MONGO_DB"
  "MORTIMER_MONGO_USERNAME"
  "MORTIMER_MONGO_PASSWORD"
  "MORTIMER_MONGO_AUTH_SOURCE"
  "ALFRED_DB_NAME"
)

missing=0
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    log "Environment variable '${var}' must be set"
    missing=1
  fi
done

if [[ "${missing}" -eq 1 ]]; then
  log "Missing mandatory environment variables. Aborting startup."
  exit 1
fi

INSTANCE_PATH=${MORTIMER_INSTANCE_PATH:-/app/instance}
LOG_DIR_DEFAULT=${MORTIMER_LOG_DIR:-/app/log}
LOG_FILE=${MORTIMER_LOG_FILE:-${LOG_DIR_DEFAULT%/}/mortimer.log}

mkdir -p "${INSTANCE_PATH}" "${LOG_DIR_DEFAULT}"
if [[ ! -f "${INSTANCE_PATH}/mortimer.conf" && -f "/app/config/mortimer.conf" ]]; then
  cp /app/config/mortimer.conf "${INSTANCE_PATH}/mortimer.conf"
  cp /app/config/alfred.conf "${INSTANCE_PATH}/alfred.conf"
fi

ALFRED_LOGFILE_DEFAULT=${ALFRED_LOGFILE:-${LOG_DIR_DEFAULT%/}/alfred.log}
export ALFRED_LOGFILE="${ALFRED_LOGFILE_DEFAULT}"
touch "${LOG_FILE}"
touch "${ALFRED_LOGFILE}"

wait_for_mongo() {
  local attempt=1
  local max_attempts=${MORTIMER_MONGO_MAX_ATTEMPTS:-10}
  local delay=1
  local backoff=2

  while true; do
    if /opt/venv/bin/python <<'PY'
import os
import sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_client_kwargs():
    uri = os.getenv("MORTIMER_MONGO_URI")
    if uri:
        return {"host": uri}

    kwargs = {
        "host": os.getenv("MORTIMER_MONGO_HOST", "mongo"),
        "port": int(os.getenv("MORTIMER_MONGO_PORT", "27017")),
        "authSource": os.getenv("MORTIMER_MONGO_AUTH_SOURCE", "admin"),
    }

    username = os.getenv("MORTIMER_MONGO_USERNAME")
    password = os.getenv("MORTIMER_MONGO_PASSWORD")
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password

    kwargs["tls"] = env_bool("MORTIMER_MONGO_SSL", False)
    tls_ca = os.getenv("MORTIMER_MONGO_TLS_CA_FILE")
    if tls_ca:
        kwargs["tlsCAFile"] = tls_ca

    return kwargs


try:
    client = MongoClient(**build_client_kwargs(), serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
except PyMongoError as exc:  # pragma: no cover - runtime guard
    print(f"MongoDB not ready: {exc}", file=sys.stderr)
    raise SystemExit(1)
else:
    client.close()
    raise SystemExit(0)
PY
    then
      log "MongoDB connection established."
      break
    fi

    if (( attempt >= max_attempts )); then
      log "MongoDB did not become ready after ${attempt} attempts."
      exit 1
    fi

    log "MongoDB not ready yet. Retrying in ${delay}s..."
    sleep "${delay}"
    attempt=$((attempt + 1))
    delay=$((delay * backoff))
    if (( delay > 30 )); then
      delay=30
    fi
  done
}

wait_for_mongo

APP_VERSION=$(/opt/venv/bin/python - <<'PY'
from mortimer import __version__
print(__version__)
PY
)

log "Starting Mortimer v${APP_VERSION}"
export MORTIMER_INSTANCE_PATH="${INSTANCE_PATH}"
export MORTIMER_LOG_FILE="${LOG_FILE}"

cd /app
exec "$@"
