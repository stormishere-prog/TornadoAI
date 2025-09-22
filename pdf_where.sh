#!/data/data/com.termux/files/usr/bin/sh
set -eu
CACHE="/storage/emulated/0/Download/TornadoAI/cache"

if [ $# -ne 1 ]; then
  echo "usage: sh pdf_where.sh <hash>.pdf" >&2
  exit 1
fi

f="$CACHE/$1"
if [ -s "$f.path" ]; then
  cat "$f.path"
else
  echo "no pointer found for $1" >&2
  exit 1
fi
