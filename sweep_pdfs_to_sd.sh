#!/data/data/com.termux/files/usr/bin/sh
set -eu
. /storage/emulated/0/Download/TornadoAI/ta_paths.conf

mkdir -p "$CACHE" "$SDPDF"

count_moved=0
count_pointer=0
count_skipped=0

# Move existing cached PDFs to SD; leave tiny pointer in cache
find "$CACHE" -maxdepth 1 -type f -name '*.pdf' | while read -r p; do
  base="$(basename "$p")"
  dst="$SDPDF/$base"
  pathfile="$CACHE/$base.path"

  # Move to SD if needed
  if [ ! -e "$dst" ]; then
    mv "$p" "$dst" && count_moved=$((count_moved+1)) || true
  else
    # SD already has it; drop the cache file to save space
    rm -f "$p"
    count_skipped=$((count_skipped+1))
  fi

  # Always create/update a pointer .path file (symlinks aren’t allowed here)
  printf '%s\n' "$dst" > "$pathfile"
  # Ensure there’s a tiny placeholder file so tools expecting *.pdf in cache don’t crash
  : > "$CACHE/$base"
  count_pointer=$((count_pointer+1))
done

echo "[sweep] moved=$count_moved pointer_files=$count_pointer skipped=$count_skipped"
