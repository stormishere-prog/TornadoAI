#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="/storage/emulated/0/Download/TornadoAI"
cd "$ROOT"
mkdir -p alerts

for f in harvester.log harvester.out alerts/alerts_case.log alerts/alerts.jsonl alerts/alerts.log; do
  if [ -f "$f" ]; then
    ts=$(date +%Y%m%d-%H%M%S)
    cp "$f" "${f}.${ts}"
    : > "$f"
    gzip -f "${f}.${ts}" || true
  fi
done

# keep last 3 per log
find . -type f -name "*.gz" | while read -r g; do
  base=$(echo "$g" | sed -E 's/\.[0-9]{8}-[0-9]{6}\.gz$//')
  ls -1t "${base}".*.gz 2>/dev/null | awk 'NR>3' | xargs -r rm -f
done
