#!/data/data/com.termux/files/usr/bin/sh
cd /storage/emulated/0/Download/TornadoAI || exit 1
sqlite3 -cmd '.timeout 2000' corpus.db "
SELECT datetime(ts_utc,'unixepoch') AS ts,
       mime,
       media_url,
       page_url
FROM media_refs
ORDER BY ts_utc DESC
LIMIT 20;"
