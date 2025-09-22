#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT"

JSON=$(sh ./safe_run.sh python3 mark_evidence_snapshot.py "$@")
echo "$JSON"
ID=$(printf '%s' "$JSON" | jq -r '.evidence_id')
[ -n "$ID" ] && sh ./safe_run.sh python3 propaganda_explain.py --id "$ID" >/dev/null 2>&1 || true
