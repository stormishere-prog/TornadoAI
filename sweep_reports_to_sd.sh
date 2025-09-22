#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
SRC="$ROOT/reports"
DST="/storage/6F3A-4D77/Documents/TornadoAI/reports"
mkdir -p "$DST" "$SRC"

# move case folders and top-level files
find "$SRC" -maxdepth 1 -type f \( -name "*.md" -o -name "*.csv" -o -name "*.zip" \) | while read -r f; do
  base=$(basename "$f")
  mv -f "$f" "$DST/$base" 2>/dev/null || continue
  printf '%s\n' "$DST/$base" > "$SRC/$base.path"
  echo "[sweep_reports] moved file: $base -> SD"
done

# case subfolders (copy whole folder then prune locally)
find "$SRC/cases" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read -r d; do
  case_name=$(basename "$d")
  mkdir -p "$DST/cases"
  # rsync not available by default; use cp -a then remove locally
  cp -a "$d" "$DST/cases/$case_name"
  rm -rf "$d"
  printf '%s\n' "$DST/cases/$case_name" > "$SRC/cases/$case_name.path"
  echo "[sweep_reports] moved case: $case_name -> SD"
done
