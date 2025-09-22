#!/data/data/com.termux/files/usr/bin/sh
set -e
DIR="/storage/emulated/0/Download/TornadoAI"
cd "$DIR"
PORT=$(cat port.txt 2>/dev/null || true)
[ -z "$PORT" ] && { echo "router not started (port.txt missing)"; exit 1; }
echo "PORT=$PORT"
curl -s "http://127.0.0.1:$PORT/api/health"; echo
curl -s "http://127.0.0.1:$PORT/api/port"; echo
