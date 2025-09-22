#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT"
CASE="${1:?usage: case_mark_batch.sh <CaseName> <query> [urlfilter] [limit]}"
QUERY="${2:?need query}"
URLF="${3:-}"
LIMIT="${4:-10}"

# always run through safe_run (schema guard) if present
RUNNER="python3"
[ -x "./safe_run.sh" ] && RUNNER="sh ./safe_run.sh python3"

exec $RUNNER case_mark.py --case "$CASE" --from-search "$QUERY" ${URLF:+--urlfilter "$URLF"} --limit "$LIMIT"
