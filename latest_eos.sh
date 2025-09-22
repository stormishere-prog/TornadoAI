#!/data/data/com.termux/files/usr/bin/sh
cd /storage/emulated/0/Download/TornadoAI || exit 1
sqlite3 -cmd '.timeout 2000' corpus.db "
SELECT datetime(ts_utc,'unixepoch') AS ts,
       substr(title,1,100) AS title,
       url
FROM docs
WHERE url LIKE 'https://www.whitehouse.gov/presidential-actions/%'
ORDER BY ts_utc DESC
LIMIT 10;"
