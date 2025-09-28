#!/usr/bin/env sh
set -eu

exec gunicorn mortimer_docker.wsgi:app --config /app/gunicorn.conf.py --bind 0.0.0.0:8001
