#!/bin/zsh
set -e
cd /Users/mohyi/CHATGPT/casablanca_watch
if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then
  curl -fsS -X POST http://127.0.0.1:8765/api/scan
  open http://127.0.0.1:8765
else
  /Users/mohyi/CHATGPT/.venv/bin/python /Users/mohyi/CHATGPT/casablanca_watch/watch.py scan --notify stdout
fi
