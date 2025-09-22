#!/data/data/com.termux/files/usr/bin/sh
set -e
ROOT="/storage/emulated/0/Download/TornadoAI"
BD="$ROOT/backups"
KEEP="$BD/corpus.pre-guard.db"

mkdir -p "$BD"

# Promote newest timestamped backup to the single keeper (if any)
latest="$(ls -1t "$BD"/corpus.*.db 2>/dev/null | head -n 1 || true)"
if [ -n "$latest" ] && [ -f "$latest" ]; then
  cp -f -- "$latest" "$KEEP.tmp"
  mv -f -- "$KEEP.tmp" "$KEEP"
fi

# Delete EVERYTHING else in backups, keep only the single keeper
# (also removes .path/.journal/.tmp cruft)
find "$BD" -maxdepth 1 -type f ! -name "$(basename "$KEEP")" -print -delete >/dev/null 2>&1 || true
echo "[prune] $(date "+%F %T") pruned to single keeper" >> "/storage/emulated/0/Download/TornadoAI/harvester.log"
exit 0

echo "[prune] $(date "+%F %T") pruned to single keeper" >> "/storage/emulated/0/Download/TornadoAI/harvester.log"
