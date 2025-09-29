# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

WORKDIR /build

COPY deploy/docker/requirements.app.in ./requirements.app.in
COPY deploy/docker/uv.app.lock ./uv.app.lock

RUN uv venv /opt/venv \
    && uv pip sync --python /opt/venv/bin/python uv.app.lock

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    MORTIMER_CONFIG=/app/config

RUN adduser --disabled-password --gecos "" mortimer

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY deploy/docker/gunicorn.conf.py ./gunicorn.conf.py
COPY deploy/docker/wsgi.py ./mortimer_docker/wsgi.py
COPY deploy/docker/entrypoint.sh ./entrypoint.sh
COPY deploy/docker/mortimer.conf ./config/mortimer.conf
COPY deploy/docker/alfred.conf ./config/alfred.conf
COPY deploy/docker/start.sh /app/start.sh

RUN chmod +x /app/start.sh

RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/instance /app/log /app/mortimer_docker \
    && chown -R mortimer:mortimer /app /opt/venv

USER mortimer

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/start.sh"]
