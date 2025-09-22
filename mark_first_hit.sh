#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT"

if [ $# -lt 1 ]; then
  echo "usage: sh ./mark_first_hit.sh <search terms...>" >&2
  exit 2
fi

Q="$*"
HIT="$(python3 search_pages.py $Q --limit 1)"
LEN="$(printf '%s' "$HIT" | jq '.hits|length')"

if [ "$LEN" -gt 0 ]; then
  URL="$(printf '%s' "$HIT" | jq -r '.hits[0].url')"
  PAGE="$(printf '%s' "$HIT" | jq -r '.hits[0].page')"
  SNIP="$(printf '%s' "$HIT" | jq -r '.hits[0].snippet' | tr -d '"')"
  # run through your evid schema guard + auto-case mark
  sh ./safe_run.sh python3 auto_case_mark.py \
      --url "$URL" --page "$PAGE" --quote "$SNIP" --note "auto-mark" --from-search "$Q"
else
  echo '{"ok":false,"error":"no hits"}'
fi
