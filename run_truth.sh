#!/data/data/com.termux/files/usr/bin/sh
ROOT="/storage/emulated/0/Download/TornadoAI"
exec sh "$ROOT/scripts/run_truth.sh"

sh "$ROOT/force_one_backup.sh" >/dev/null 2>&1 || true
