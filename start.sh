#!/data/data/com.termux/files/usr/bin/sh
set -e
DIR="/storage/emulated/0/Download/TornadoAI"
cd "$DIR"
sh "$DIR/stop.sh" >/dev/null 2>&1 || true
: > "$DIR/router.log"
nohup python3 "$DIR/router.py" >> "$DIR/router.log" 2>&1 &
PID=$!
echo "$PID" > "$DIR/router.pid"
# Wait for port.txt to appear
for i in 1 2 3 4 5 6 7 8 9 10; do
  [ -s "$DIR/port.txt" ] && break
  sleep 0.2
done
PORT=$(cat "$DIR/port.txt" 2>/dev/null || true)
echo "Started PID=$PID PORT=${PORT:-unknown}  (log: $DIR/router.log)"
