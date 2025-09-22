#!/data/data/com.termux/files/usr/bin/sh
cd /storage/emulated/0/Download/TornadoAI || exit 1
PORT=$(cat port.txt 2>/dev/null)
[ -z "$PORT" ] && { echo "port.txt missing. Start router first."; exit 1; }
echo "PORT=$PORT"
curl -s "http://127.0.0.1:$PORT/api/health" | tr -d '\n'; echo
curl -s "http://127.0.0.1:$PORT/api/port"   | tr -d '\n'; echo
curl -s -X POST "http://127.0.0.1:$PORT/api/ping" | tr -d '\n'; echo
