"""WSGI entrypoint for the Mortimer Docker image."""

from __future__ import annotations

import os
from pathlib import Path

from mortimer import create_app


def _ensure_directory(path: str) -> str:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory)


def _instance_path() -> str:
    return _ensure_directory(os.getenv("MORTIMER_INSTANCE_PATH", "/app/instance"))


def _log_file(instance_path: str) -> str:
    log_dir_override = os.getenv("MORTIMER_LOG_DIR")
    if log_dir_override:
        log_dir = _ensure_directory(log_dir_override)
    else:
        log_dir = _ensure_directory("/app/log")

    log_file = os.getenv("MORTIMER_LOG_FILE")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        return log_file

    return str(Path(log_dir) / "mortimer.log")


def _ensure_config_path() -> None:
    default_config_dir = "/app/config"
    os.environ.setdefault("MORTIMER_CONFIG", default_config_dir)
    Path(default_config_dir).mkdir(parents=True, exist_ok=True)


_ensure_config_path()
INSTANCE_PATH = _instance_path()
LOG_FILE = _log_file(INSTANCE_PATH)

app = create_app(instance_path=INSTANCE_PATH, logfile=LOG_FILE)
