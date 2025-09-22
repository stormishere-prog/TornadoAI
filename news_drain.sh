#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT" || exit 1
QUEUE="$ROOT/news_queue.txt"
SRC="$ROOT/sources.txt"
TMP="$ROOT/.sources.tmp"

[ ! -s "$QUEUE" ] && exit 0
cut -f1 "$QUEUE" | awk 'NF' >> "$SRC"
awk '!x[$0]++' "$SRC" > "$TMP" && mv "$TMP" "$SRC"
: > "$QUEUE"
echo "[news_drain] merged queued URLs into sources.txt"
