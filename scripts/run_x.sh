#!/data/data/com.termux/files/usr/bin/sh
set -e
ROOT="/storage/emulated/0/Download/TornadoAI"
LOG="$ROOT/harvester.log"
cd "$ROOT"

echo "[run_x] $(date '+%F %T') start" >>"$LOG"

# Use your working x_proxy fetcher; gentle delay to avoid blocks
X_REQUEST_DELAY="${X_REQUEST_DELAY:-4.0}" sh ./safe_run.sh python3 x_fetch_xproxy.py >>"$LOG" 2>&1 || true

# Summaries/tags/echo/contradictions + reports; no need to rebuild feed every time
sh ./safe_run.sh python3 news_summarize.py >>"$LOG" 2>&1 || true
sh ./post_ingest.sh                      >>"$LOG" 2>&1 || true

echo "[run_x] $(date '+%F %T') done" >>"$LOG"

sh ./safe_run.sh python3 /storage/emulated/0/Download/TornadoAI/add_content_sha.py >>"$LOG" 2>&1 || true

# Auto-refresh Daily Brief after X
sh "$ROOT/brief_refresh.sh" >>"$LOG" 2>&1 || true
