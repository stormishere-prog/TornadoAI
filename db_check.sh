#!/data/data/com.termux/files/usr/bin/sh
sqlite3 -cmd ".timeout 4000" "/storage/emulated/0/Download/TornadoAI/corpus.db" "PRAGMA integrity_check;"
