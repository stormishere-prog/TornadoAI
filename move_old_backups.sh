#!/data/data/com.termux/files/usr/bin/sh
# Move older *.pre-guard.db backups to SD card, keep newest N locally.

set -e

# --- settings ---
KEEP="${KEEP:-10}"   # how many newest backups to keep locally
SRC="/storage/emulated/0/Download/TornadoAI/backups"
SD_ROOT="/storage/6F3A-4D77/Android/media/TornadoAI"
DST="$SD_ROOT/backups"

echo "[move_old_backups] source: $SRC"
echo "[move_old_backups] dest:   $DST"
mkdir -p "$DST"

# quick write test to ensure SD is writable
if ! ( echo ok > "$DST/_write_test.txt" && rm -f "$DST/_write_test.txt" ); then
  echo "ERROR: SD card path not writable: $DST" >&2
  exit 1
fi

cd "$SRC"

# 0) Clean tiny helper files (safe to delete)
rm -f -- *.path *-journal 2>/dev/null || true

# 1) If rsync exists, use it (robust). Otherwise, do manual copy.
if command -v rsync >/dev/null 2>&1; then
  echo "[move_old_backups] using rsync"
  # build list excluding newest $KEEP
  LIST="$(ls -t *pre-guard.db 2>/dev/null | tail -n +$((KEEP+1)))"
  if [ -n "$LIST" ]; then
    # copy with remove-source-files (only after success)
    rsync -av --progress --remove-source-files $LIST "$DST"/
    sync
  else
    echo "[move_old_backups] nothing to move"
  fi
else
  echo "[move_old_backups] rsync not found, using safe cp/mv loop"
  # move older entries one by one
  ls -t *pre-guard.db 2>/dev/null | tail -n +$((KEEP+1)) | \
  while IFS= read -r f; do
    [ -e "$f" ] || continue
    echo " - moving $f"
    cp -p -- "$f" "$DST/${f}.part" \
      && sync \
      && mv -- "$DST/${f}.part" "$DST/$f" \
      && rm -f -- "$f" \
      || echo "FAILED on $f" >&2
  done
fi

echo "[move_old_backups] done"
echo "Local count: $(ls -1 *pre-guard.db 2>/dev/null | wc -l) (kept newest $KEEP)"
echo "SD count:    $(ls -1 "$DST"/*pre-guard.db 2>/dev/null | wc -l)"
