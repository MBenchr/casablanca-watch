#!/bin/zsh
set -e
cd /Users/mohyi/CHATGPT/casablanca_watch
if ! curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then
  nohup /Users/mohyi/CHATGPT/.venv/bin/python /Users/mohyi/CHATGPT/casablanca_watch/watch.py serve >/Users/mohyi/CHATGPT/casablanca_watch/data/server.log 2>&1 &
  sleep 2
fi
open http://127.0.0.1:8765
