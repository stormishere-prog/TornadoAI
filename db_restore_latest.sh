#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
BKDIR="$ROOT/backups"
LAST=$(ls -1t "$BKDIR"/corpus.*.db 2>/dev/null | head -n1 || true)
[ -n "$LAST" ] || { echo "no backups found"; exit 1; }
cp "$LAST" "$ROOT/corpus.db"
echo "restored: $LAST"
