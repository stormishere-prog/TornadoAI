#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT" || exit 1

i=0
while :; do
  i=$((i+1))
  echo "[score_loop] pass $i"
  sh ./safe_run.sh python3 score_propaganda.py || true

  # stop when there are no unscored rows
  LEFT=$(sh ./safe_run.sh sqlite3 corpus.db "SELECT COUNT(*) FROM doc_pages WHERE propaganda_score IS NULL;" | tail -n1)
  case "$LEFT" in '' ) LEFT=0;; esac
  echo "[score_loop] remaining unscored: $LEFT"
  [ "$LEFT" -eq 0 ] && break

  # short nap to avoid task killer
  sleep 5
done
