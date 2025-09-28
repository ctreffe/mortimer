import multiprocessing
import os


def _int_env(key: str, default: int) -> int:
    try:
        value = int(os.getenv(key, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def _fallback_workers() -> int:
    count = multiprocessing.cpu_count() * 2 + 1
    return count if count > 0 else 3


bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = _int_env("WEB_CONCURRENCY", _fallback_workers())
threads = _int_env("GUNICORN_THREADS", 2)
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
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 0)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 0)

if max_requests == 0:
    max_requests = None
if max_requests_jitter == 0:
    max_requests_jitter = None
