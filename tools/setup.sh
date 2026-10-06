#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v git >/dev/null
command -v gfortran >/dev/null || { echo "请先安装 gfortran（macOS: brew install gcc）"; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p runs
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python tools/build.py
