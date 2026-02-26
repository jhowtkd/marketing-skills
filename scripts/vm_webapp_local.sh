#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8766}"
PID_FILE="/tmp/vm_webapp_local.pid"
LOG_FILE="/tmp/vm_webapp_local.log"

start() {
  cd "$ROOT_DIR"
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "already running (pid=$(cat "$PID_FILE"))"
    exit 0
  fi
  nohup uv run python -m vm_webapp serve --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"
  sleep 1
  echo "started pid=$(cat "$PID_FILE") port=$PORT log=$LOG_FILE"
}

stop() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    echo "stopped"
  else
    rm -f "$PID_FILE"
    echo "not running"
  fi
}

status() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "running pid=$(cat "$PID_FILE")"
  else
    echo "stopped"
  fi
}

health() {
  curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" || true
  echo
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  health) health ;;
  *) echo "usage: $0 {start|stop|status|health}"; exit 1 ;;
esac
