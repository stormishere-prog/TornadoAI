#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
TAG="$1"
sh "$ROOT/safe_run.sh" python3 "$ROOT/watchlist_ctl.py" remove --tag "$TAG"
