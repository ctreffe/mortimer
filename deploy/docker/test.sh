#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cd "${SCRIPT_DIR}"

# Builds (if needed) and starts the Mortimer + Mongo stack in the foreground.
# Press Ctrl+C to stop; logs for both services stream to the terminal.
docker compose up --build mortimer-app
