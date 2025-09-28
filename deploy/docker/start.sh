#!/usr/bin/env sh
set -eu

exec gunicorn mortimer_docker.wsgi:app --config /app/gunicorn.conf.py
