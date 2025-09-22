#!/data/data/com.termux/files/usr/bin/sh
set -e
ROOT="/storage/emulated/0/Download/TornadoAI"
CASE="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
OUT="$ROOT/reports/${CASE}.zip"
DIR="$ROOT/reports/cases/${CASE}"

if [ -z "$1" ]; then
  echo "usage: $0 <CaseName>" >&2
  exit 1
fi

if [ ! -d "$DIR" ]; then
  echo "error: case folder not found -> $DIR" >&2
  exit 1
fi

cd "$ROOT/reports/cases"
rm -f "$OUT"
zip -r "$OUT" "$CASE" >/dev/null
echo "ok: archive -> $OUT"
