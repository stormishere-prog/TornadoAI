#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
TAG="$1"
QUERY="$2"
CASE="${3:-$TAG}"
URLFILTER="${4:-%}"
PRIORITY="${5:-2}"
sh "$ROOT/safe_run.sh" python3 "$ROOT/watchlist_ctl.py" add \
  --tag "$TAG" --query "$QUERY" --urlfilter "$URLFILTER" --case "$CASE" --priority "$PRIORITY"
