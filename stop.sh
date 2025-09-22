#!/data/data/com.termux/files/usr/bin/sh
set -eu
DIR="/storage/emulated/0/Download/TornadoAI"
PIDFILE="$DIR/router.pid"
PORTFILE="$DIR/port.txt"

kill_pid() {
  [ -z "${1:-}" ] && return 0
  if ps -p "$1" >/dev/null 2>&1; then
    kill "$1" 2>/dev/null || true
    sleep 0.4
    ps -p "$1" >/dev/null 2>&1 && kill -9 "$1" 2>/dev/null || true
  fi
}

PID=""
[ -f "$PIDFILE" ] && PID=$(cat "$PIDFILE" 2>/dev/null || true) || true
[ -n "$PID" ] && echo "Stopping PID $PID..." || echo "No PID file."
kill_pid "${PID:-}"

rm -f "$PIDFILE"
echo "Stopped."
