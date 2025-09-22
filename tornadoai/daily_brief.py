#!/data/data/com.termux/files/usr/bin/python3
import os, sqlite3, shutil, textwrap, time, html

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

width = shutil.get_terminal_size((92,20)).columns
wrap  = lambda s: "\n".join(textwrap.fill(s, width=width) for s in (s or "").splitlines())
now   = int(time.time()); since = now - 24*3600

# trust buckets (same as ask_local, but inline)
TRUST = {"official":0.90, "independent":0.60, "state_media":0.35, "propaganda":0.20, "unknown":0.50}

def score(trust, echoes, contr):
    echo_penalty  = min(0.20, 0.02 * max(0, echoes or 0))
    contr_penalty = min(0.25, 0.05 * max(0, contr or 0))
    s = max(0.05, min(0.99, (trust or 0.50) - echo_penalty - contr_penalty))
    return int(round(s*100))

Q_MAIN = """
WITH e AS (
  SELECT canon, COUNT(*) AS n FROM echo_edges GROUP BY canon
),
k AS (
  SELECT a_url AS url, COUNT(*) AS contr FROM contradictions GROUP BY a_url
  UNION ALL
  SELECT b_url AS url, COUNT(*) AS contr FROM contradictions GROUP BY b_url
),
kk AS (
  SELECT url, SUM(contr) AS contr FROM k GROUP BY url
)
SELECT
  d.ts_utc,
  IFNULL(d.title,'') AS title,
  IFNULL(s.summary,'') AS summary,
  d.url,
  IFNULL(d.source_tag,'') AS tag,
  IFNULL(d.doc_type,'')  AS dtype,
  IFNULL(dp.content, IFNULL(d.content,'')) AS body,
  IFNULL(e.n,0) AS echoes,
  IFNULL(kk.contr,0) AS contr
FROM docs d
LEFT JOIN doc_summaries s ON d.url=s.url
LEFT JOIN doc_pages dp     ON dp.url=d.url AND dp.page_no=1
LEFT JOIN e ON e.canon=d.canon
LEFT JOIN kk ON kk.url=d.url
WHERE d.ts_utc>=? AND d.doc_type IN ('truth','x')
ORDER BY d.ts_utc DESC
LIMIT 400
"""

def tag_bucket(t):
    if not t: return "unknown"
    if t.startswith("official"):    return "official"
    if t.startswith("independent"): return "independent"
    if t.startswith("state_media"): return "state_media"
    if t.startswith("propaganda"):  return "propaganda"
    return "unknown"

def host(u):
    try:
        import urllib.parse
        n=urllib.parse.urlparse(u).netloc.lower()
        return n.lstrip("www.") or "(unknown)"
    except:
        return "(unknown)"

with sqlite3.connect(DB, timeout=60) as c:
    c.execute("PRAGMA foreign_keys=ON;")
    rows = c.execute(Q_MAIN, (since,)).fetchall()

if not rows:
    print("(no Truth/X items in last 24h)"); raise SystemExit()

# header
print("="*width)
print(time.strftime("Daily Brief — %Y-%m-%d %H:%M", time.localtime(now)))
print("-"*width)

# per-source counters
import collections
by_src = collections.Counter()
by_tag = collections.Counter()

for r in rows:
    ts, title, summary, url, tag, dtype, body, echoes, contr = r
    bucket = tag_bucket(tag)
    by_src[host(url)] += 1
    by_tag[bucket]    += 1
    trust = TRUST.get(bucket, 0.50)
    conf  = score(trust, echoes, contr)
    ttl   = (title or "").strip() or "(untitled)"
    text  = (summary or body or ttl).strip()
    # show card
    print(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(int(ts)))}  [{dtype}]  <{bucket}>  conf={conf}%  echo={echoes}  contra={contr}")
    print(ttl)
    print("-"*width)
    print(wrap(text))
    print(url)
    print("-"*width)

# footer: small summary
print("="*width)
print("Last 24h counts by source (top 8):")
for k,v in by_src.most_common(8):
    print(f"  {k:35s} {v:>3}")
print("By tag bucket:")
for b in ("official","independent","state_media","propaganda","unknown"):
    if by_tag[b]: print(f"  {b:12s} {by_tag[b]:>3}")
