import multiprocessing
import os


def _int_env(key: str, default: int, *, allow_zero: bool = False) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default

    raw = raw.strip()
    if raw == "":
        return default

    lowered = raw.lower()
    if lowered in {"none", "null", "disable", "disabled"}:
        return 0 if allow_zero else default

    try:
        value = int(raw, 10)
    except (TypeError, ValueError):
        return default

    if value < 0:
        return default
    if value == 0 and not allow_zero:
        return default
    return value


def _fallback_workers() -> int:
    count = multiprocessing.cpu_count() * 2 + 1
    return count if count > 0 else 3


bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")  # Overwritten in start.sh
workers = _int_env("WEB_CONCURRENCY", 1)
threads = _int_env("GUNICORN_THREADS", 10)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = "*"

capture_output = True
preload_app = False
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)
timeout = _int_env("GUNICORN_TIMEOUT", 60)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 0, allow_zero=True)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 0, allow_zero=True)
