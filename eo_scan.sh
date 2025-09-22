#!/data/data/com.termux/files/usr/bin/sh
cd /storage/emulated/0/Download/TornadoAI || exit 1
sqlite3 -json corpus.db "
WITH hits AS (
  SELECT p.url, p.page_no,
         substr(p.text,1,500) AS snip,
         d.title,
         CASE
           WHEN p.text LIKE '%it is hereby ordered%' THEN 3
           WHEN p.text LIKE '%by the authority vested in me%' THEN 2
           WHEN d.title LIKE '%Executive Order%' THEN 1
           ELSE 0
         END AS score
  FROM doc_pages p
  JOIN docs d ON d.url=p.url
  WHERE p.url LIKE 'https://www.whitehouse.gov/presidential-actions/%'
)
SELECT url, title, page_no AS page, snip
FROM hits
WHERE score>0
GROUP BY url
ORDER BY MAX(score) DESC, url DESC
LIMIT 10;
"
