#!/data/data/com.termux/files/usr/bin/python3
# Minimal RSS/Atom + HTML ingester -> corpus.db
# Safe for Termux. No extra deps.

import os, sys, re, time, sqlite3, hashlib
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from xml.etree import ElementTree as ET

ROOT = os.path.abspath(os.getcwd())
DB   = os.path.join(ROOT, "corpus.db")
SRC  = os.path.join(ROOT, "news_sources.txt")
BAK  = os.path.join(ROOT, "backups")

UA = "Mozilla/5.0 (Linux; Android) TornadoAI/1.0 (+termux)"
TIMEOUT = 6

os.makedirs(BAK, exist_ok=True)

def db():
    init = not os.path.exists(DB)
    con = sqlite3.connect(DB, timeout=10, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=FULL;")
    con.execute("PRAGMA temp_store=FILE;")
    con.execute("PRAGMA foreign_keys=ON;")
    if init: _init_schema(con)
    return con

def _init_schema(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
      url TEXT PRIMARY KEY,
      title TEXT,
      content TEXT,
      ts_utc INTEGER,
      source_trust INTEGER DEFAULT 0,
      sha256 TEXT
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
      title, content, url UNINDEXED, tokenize='unicode61'
    );

    CREATE TABLE IF NOT EXISTS evidence_log(
      ts_utc INTEGER,
      source TEXT,
      snippet TEXT,
      tags TEXT,
      sha256 TEXT,
      score_breakdown TEXT
    );

    CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
      INSERT INTO docs_fts(rowid, title, content, url)
      VALUES (new.rowid, new.title, new.content, new.url);
    END;
    CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
      INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
      VALUES('delete', old.rowid, old.title, old.content, old.url);
    END;
    CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
      INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
      VALUES('delete', old.rowid, old.title, old.content, old.url);
      INSERT INTO docs_fts(rowid, title, content, url)
      VALUES (new.rowid, new.title, new.content, new.url);
    END;
    """)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE);")

def backup(c):
    # One backup per day
    stamp = time.strftime("%Y%m%d")
    path = os.path.join(BAK, f"corpus_{stamp}.db")
    if not os.path.exists(path):
        c.execute(f"VACUUM main INTO '{path}';")

def http_get(url):
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type","text/plain") or "").lower()
            data  = r.read()
        # try utf-8, fall back latin-1
        try: text = data.decode("utf-8", "ignore")
        except: text = data.decode("latin-1", "ignore")
        return text, ctype
    except (URLError, HTTPError) as e:
        return "", ""
    except Exception:
        return "", ""

def strip_html(t):
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", t or "")
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()

def propaganda_tags(text):
    low = (text or "").lower()
    pats = [
      ("anonymous sources", "appeal_to_authority"),
      ("experts say", "appeal_to_authority"),
      ("breaking", "sensational"),
      ("shocking", "sensational"),
      ("must see", "clickbait"),
      ("debunked", "framing"),
      ("fact check", "framing"),
    ]
    hits = {tag for key,tag in pats if key in low}
    return ",".join(hits or ["clean"])

def sha(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def parse_rss_atom(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items

    # RSS
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        items.append((title, link, strip_html(desc)))
    # Atom
    for entry in root.findall(".//{*}entry"):
        title = (entry.findtext("{*}title") or "").strip()
        linkel = entry.find("{*}link")
        link = (linkel.get("href") if (linkel is not None and linkel.get("href")) else "").strip()
        summ  = (entry.findtext("{*}summary") or entry.findtext("{*}content") or "").strip()
        items.append((title, link, strip_html(summ)))
    return items

def upsert_doc(c, url, title, content, trust=50):
    now = int(time.time())
    c.execute("""
      INSERT INTO docs(url,title,content,ts_utc,source_trust,sha256)
      VALUES(?,?,?,?,?,?)
      ON CONFLICT(url) DO UPDATE SET
        title=excluded.title,
        content=excluded.content,
        ts_utc=excluded.ts_utc,
        source_trust=excluded.source_trust,
        sha256=excluded.sha256
    """, (url, title, content, now, trust, sha(title+content)))

def add_evidence(c, source, snippet, tags, kind):
    c.execute("""
      INSERT INTO evidence_log(ts_utc,source,snippet,tags,sha256,score_breakdown)
      VALUES(?,?,?,?,?,?)
    """, (int(time.time()), source, snippet[:800], tags, "", kind))

def ingest_source(c, src):
    text, ctype = http_get(src)
    if not text:
        return 0
    is_xml = ("xml" in ctype) or src.endswith(".xml") or src.endswith("/feed/") or text.lstrip().startswith("<")
    added = 0
    if is_xml:
        items = parse_rss_atom(text)
        for (title, link, summary) in items[:30]:
            body = (summary or title or "")[:1500]
            if not (title or body): 
                continue
            tgs = propaganda_tags(body)
            add_evidence(c, link or src, f"{title} — {body}", tgs, "news_rss")
            key = link or (src + "#" + (title[:60] if title else "item"))
            upsert_doc(c, key, title or "(untitled)", body, trust=60)
            added += 1
    else:
        snippet = strip_html(text)[:1500]
        tgs = propaganda_tags(snippet)
        add_evidence(c, src, snippet, tgs, "news_html")
        upsert_doc(c, src, "(page)", snippet, trust=40)
        added += 1
    return added

def main():
    if not os.path.exists(SRC):
        print('{"ok": false, "error": "news_sources.txt not found"}')
        sys.exit(1)

    sources = []
    with open(SRC, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"): 
                continue
            sources.append(s)

    con = db()
    backup(con)  # daily backup

    total = 0
    con.execute("BEGIN IMMEDIATE;")
    try:
        for src in sources[:12]: # keep it light on phone data
            total += ingest_source(con, src)
        con.execute("COMMIT;")
    except Exception as e:
        con.execute("ROLLBACK;")
        print('{"ok": false, "error": "ingest_failed"}')
        raise
    finally:
        con.close()

    print(f'{{"ok": true, "added": {total}}}')

if __name__ == "__main__":
    main()
