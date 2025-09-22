#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT" || exit 1

echo "[1/5] disk usage before:"
df -h "$ROOT" | sed '1,1!d;'
du -h -d1 "$ROOT" | sort -h | tail -n 20

# prune PDF cache older than 14 days
[ -d cache ] && find cache -type f -mtime +14 -print -delete || true

# keep only 5 most recent DB backups
if [ -d backups ]; then
  ls -1t backups/corpus.*.db 2>/dev/null | awk 'NR>5' | while read -r f; do
    echo "delete old backup: $f"
    rm -f -- "$f"
  done
fi

# shrink DB
sqlite3 -cmd ".timeout 6000" corpus.db "PRAGMA optimize; VACUUM;"

echo "[2/5] prune old harvester logs over 7d"
find . -maxdepth 1 -type f -name "harvester*.out" -mtime +7 -print -delete || true
find . -maxdepth 1 -type f -name "harvester*.log" -mtime +14 -print -delete || true

echo "[3/5] list largest files:"
ls -lSh | head -n 30

echo "[4/5] disk usage after:"
df -h "$ROOT" | sed '1,1!d;'
du -h -d1 "$ROOT" | sort -h | tail -n 20

echo "[5/5] done."
