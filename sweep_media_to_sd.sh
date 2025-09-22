#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
SRC="$ROOT/media_cache"
DST="/storage/6F3A-4D77/Documents/TornadoAI/media_cache"
mkdir -p "$DST" "$SRC"

find "$SRC" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.webm" -o -name "*.mp3" -o -name "*.m4a" \) | while read -r f; do
  base=$(basename "$f")
  mv -f "$f" "$DST/$base" 2>/dev/null || continue
  printf '%s\n' "$DST/$base" > "$SRC/$base.path"
  echo "[sweep_media] moved: $base -> SD"
done
