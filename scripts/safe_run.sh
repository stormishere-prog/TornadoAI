#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT"

# A) heal/unlock + backup + integrity check
python3 db_guard.py

# B) ensure evidence schema before anything else
python3 evidence_migrate.py

# C) pass-through to the real command
exec "$@"

# --- auto-prune backups (silent on failure) ---
if [ -x "/storage/emulated/0/Download/TornadoAI/prune_backups.sh" ]; then
  /storage/emulated/0/Download/TornadoAI/prune_backups.sh >/dev/null 2>&1 || true
fi
# ----------------------------------------------
