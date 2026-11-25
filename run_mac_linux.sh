#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  SciGram — AI Detection & Scientific Structure Analyzer"
echo "============================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 (3.10+) was not found. Install it from https://www.python.org/downloads/"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/2] Creating isolated virtual environment (.venv)..."
  python3 -m venv .venv
  echo "[2/2] Installing SciGram dependencies (first-time setup)..."
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e .
fi

echo ""
echo "Starting SciGram Web Dashboard at http://127.0.0.1:8000 ..."
echo "(First launch will download ~158 MB of quantized neural models once)"
echo "Press Ctrl+C to stop."
echo ""

(
  sleep 3
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
  fi
) &

exec .venv/bin/python server.py
