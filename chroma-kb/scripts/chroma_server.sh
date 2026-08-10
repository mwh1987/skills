#!/bin/bash
# Start/stop the Chroma DB server
set -e

DATA_DIR="/home/mwh1987/.openclaw/workspace/chroma-data"
PORT=8000
HOST="127.0.0.1"

case "$1" in
  start)
    if pgrep -f "chroma run" > /dev/null; then
      echo "Chroma server already running"
    else
      chroma run --path "$DATA_DIR" --port $PORT --host $HOST &
      sleep 3
      echo "Chroma server started at http://$HOST:$PORT"
    fi
    ;;
  stop)
    pkill -f "chroma run" 2>/dev/null || true
    echo "Chroma server stopped"
    ;;
  status)
    if pgrep -f "chroma run" > /dev/null; then
      echo "Chroma server running"
      curl -s http://$HOST:$PORT/api/v2/heartbeat
    else
      echo "Chroma server not running"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|status}"
    ;;
ac
