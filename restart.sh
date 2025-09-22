#!/data/data/com.termux/files/usr/bin/sh
DIR="/storage/emulated/0/Download/TornadoAI"
pkill -f "$DIR/router.py" 2>/dev/null
sleep 1
# Start and wait 1s, then print last log lines if it died
nohup python3 "$DIR/router.py" >> "$DIR/router.log" 2>&1 &
PID=$!
sleep 1
if ps -p $PID >/dev/null 2>&1; then
  echo "Restarted router.py (PID: $PID). Logs: $DIR/router.log"
else
  echo "Router exited immediately. Last log lines:" 
  tail -n 40 "$DIR/router.log"
fi
