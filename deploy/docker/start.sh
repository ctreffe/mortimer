#!/usr/bin/env sh
set -eu

: "${APP_PORTS:?Set APP_PORTS, e.g. '8001 8002 8003'}"
: "${GUNICORN_APP:=mortimer_docker.wsgi:app}"
: "${GUNICORN_OPTS:=--config /app/gunicorn.conf.py}"

pids=""

for p in $APP_PORTS; do
  echo "Starting Gunicorn on :$p"
  gunicorn -w 1 -b 0.0.0.0:$p $GUNICORN_OPTS $GUNICORN_APP &
  pids="$pids $!"
done

# forward signals to children and wait
term() { echo "TERM caught; killing:$pids"; kill -TERM $pids 2>/dev/null || true; wait; }
trap term TERM INT
wait
