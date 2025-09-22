#!/data/data/com.termux/files/usr/bin/sh
DIR="/storage/emulated/0/Download/TornadoAI"
PORT=$(awk '/^PORT *=/{print $3}' "$DIR/router.py")
PID=$(pgrep -f "$DIR/router.py")
[ -n "$PID" ] && echo "router.py running (PID $PID)" || echo "router.py not running"
# Try to check port (ss may be restricted on some devices)
ss -ltnp 2>/dev/null | grep ":$PORT" || echo "port $PORT: (no listener)"
echo "Configured port: $PORT"
