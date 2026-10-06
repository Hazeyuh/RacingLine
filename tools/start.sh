#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec .venv/bin/python tools/server.py "${1:-8765}"
