#!/data/data/com.termux/files/usr/bin/python3
import os, re, sys, json, time, sqlite3

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

Q=" ".join(sys.argv[1:]).strip()
if not Q:
    print("usage: ask_local.py <question>"); sys.exit(1)

def norm(t): return re.sub(r'\s+',' ', (t or "")).strip()

def score_conf(bucket,hits,echo,contr):
    base = {"official":0.90, "independent":0.70, "state_media":0.45, "propaganda":0.25}.get(bucket,0.50)
    base += min(0.10, 0.02*max(0,hits-1))                 # more hits, small boost
    base -= min(0.10, 0.02*max(0,int(round(echo))-1))     # bigger echo cluster, small penalty
    base -= min(0.30, 0.15*contr)                         # each contradiction hurts
    return max(0.05, min(0.99, base))

# ---- Build a safe FTS5 literal: keep alphanum words only
words = re.findall(r"[A-Za-z0-9]{2,}", Q)
Q_match_lit = "'" + " ".join(words).replace("'", "''") + "'"  # inline SQL literal

with sqlite3.connect(DB, timeout=20) as c:
    c.execute("PRAGMA query_only=ON;")
    sql_pages = f"""
      WITH hits AS (
        SELECT rowid, bm25(pages_fts, 1.0, 0.5, 0.2, 0.2) AS rank
        FROM pages_fts
        WHERE pages_fts MATCH {Q_match_lit}
        ORDER BY rank
        LIMIT 12
      )
      SELECT d.url,
             IFNULL(d.title,'')       AS title,
             IFNULL(d.source_tag,'')  AS tag,
             IFNULL(d.canon,'')       AS canon,
             snippet(pages_fts, -1, '[', ']', ' … ', 16) AS snip,
             h.rank
      FROM hits h
      JOIN doc_pages  ON doc_pages.id = h.rowid
      JOIN pages_fts  ON pages_fts.rowid = h.rowid
      JOIN docs d     ON d.url = doc_pages.url
      ORDER BY h.rank
    """
    rows = c.execute(sql_pages).fetchall()

    if not rows:
        sql_docs = f"""
          WITH hits AS (
            SELECT rowid
            FROM docs_fts
            WHERE docs_fts MATCH {Q_match_lit}
            LIMIT 8
          )
          SELECT d.url,
                 IFNULL(d.title,''),
                 IFNULL(d.source_tag,''),
                 IFNULL(d.canon,''),
                 substr(d.content,1,340),
                 0.0
          FROM hits
          JOIN docs d ON d.rowid = hits.rowid
          ORDER BY d.ts_utc DESC
        """
        rows = c.execute(sql_docs).fetchall()

# enrich with echo + contradiction counts
with sqlite3.connect(DB, timeout=20) as c:
    out=[]
    for url,title,tag,canon,snip,_ in rows:
        echo = c.execute("SELECT COUNT(*) FROM echo_edges WHERE canon=?", (canon,)).fetchone()[0] if canon else 1
        contr = c.execute("SELECT COUNT(*) FROM contradictions WHERE a_url=? OR b_url=?", (url,url)).fetchone()[0]
        out.append((url,title,tag,canon,norm(snip),echo,contr))

buckets={"official":0,"independent":0,"state_media":0,"propaganda":0,"unknown":0}
for _,_,tag,_,_,_,_ in out:
    if   tag.startswith("official"):     buckets["official"]+=1
    elif tag.startswith("independent"):  buckets["independent"]+=1
    elif tag.startswith("state_media"):  buckets["state_media"]+=1
    elif tag.startswith("propaganda"):  buckets["propaganda"]+=1
    else:                                buckets["unknown"]+=1
bucket = max(buckets, key=buckets.get) if out else "unknown"

avg_echo = (sum(e for *_,e,_ in out)/max(1,len(out))) if out else 1.0
conf = score_conf(bucket, hits=len(out), echo=avg_echo, contr=sum(c for *_,c in out))
label = "FACT" if conf>=0.90 else "GUESS"

snips=[s for *_,s,__,__ in [(u,t,tag,cn,s,e,c) for u,t,tag,cn,s,e,c in out] if s][:3]
summary = " ".join(snips) if snips else "(no good snippets; open sources below)"

print(f"{label} ({int(round(conf*100))}%)")
print(summary.strip())
print("")
print("SOURCES:")
for i,(url,title,tag,canon,snip,echo,contr) in enumerate(out[:6], start=1):
    if   tag.startswith("official"):     bucket_show="official"
    elif tag.startswith("independent"):  bucket_show="independent"
    elif tag.startswith("state_media"):  bucket_show="state_media"
    elif tag.startswith("propaganda"):  bucket_show="propaganda"
    else:                                bucket_show="unknown"
    print(f"{i}. {title or '(untitled)'}")
    print(f"   {url}")
    print(f"   tag={bucket_show}  echoes≈{echo}  contradictions={contr}")
