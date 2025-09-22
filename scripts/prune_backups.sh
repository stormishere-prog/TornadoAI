#!/data/data/com.termux/files/usr/bin/sh
# prune_backups.sh — keep storage lean
# - Local: keep 2 newest backups
# - SD card: keep files from last 3 hours, delete older

set -e

SRC="/storage/emulated/0/Download/TornadoAI/backups"
SD_ROOT="/storage/6F3A-4D77/Android/media/TornadoAI"
DST="$SD_ROOT/backups"

KEEP_LOCAL=2
HOURS_SD=3

mkdir -p "$DST"

cd "$SRC" 2>/dev/null || { echo "Local backups dir not found: $SRC"; exit 1; }

# Clean sidecar junk
rm -f -- *.path *-journal 2>/dev/null || true

# Move all but newest $KEEP_LOCAL to SD (safe copy then delete local)
ls -t *pre-guard.db 2>/dev/null | tail -n +$((KEEP_LOCAL+1)) | \
while IFS= read -r f; do
  [ -e "$f" ] || continue
  echo "Moving $f -> SD"
  cp -p -- "$f" "$DST/${f}.part" && sync && mv -- "$DST/${f}.part" "$DST/$f" && rm -f -- "$f" \
    || echo "FAILED moving $f" >&2
done

# On SD: delete backups older than HOURS_SD
find "$DST" -type f -name '*pre-guard.db' -mmin +$((HOURS_SD*60)) -print -delete 2>/dev/null || true

echo "Done."
echo " • Kept $KEEP_LOCAL newest locally in: $SRC"
echo " • SD retained last ~${HOURS_SD}h in: $DST"
