#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
SRC="$ROOT/backups"
DST="/storage/6F3A-4D77/Documents/TornadoAI/backups"
mkdir -p "$DST" "$SRC"

# list backups newest first; keep top2; move the rest
ls -1t "$SRC"/corpus.*.db 2>/dev/null | awk 'NR>2' | while read -r f; do
  base=$(basename "$f")
  mv -f "$f" "$DST/$base" 2>/dev/null || continue
  # leave a tiny pointer so tooling can find it if needed (manual check)
  printf '%s\n' "$DST/$base" > "$SRC/$base.path"
  echo "[sweep_backups] moved: $base -> SD"
done
