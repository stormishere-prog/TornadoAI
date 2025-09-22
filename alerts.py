#!/data/data/com.termux/files/usr/bin/python3
import os, sys, sqlite3, time, json, re
ROOT   = "/storage/emulated/0/Download/TornadoAI"
DB     = os.path.join(ROOT, "corpus.db")
WATCH  = os.path.join(ROOT, "watchlist.tsv")
OUTDIR = os.path.join(ROOT, "alerts")
os.makedirs(OUTDIR, exist_ok=True)

def _conn(db):
    for delay in (0.2,0.5,1,1.5,2,3):
        try:
            c = sqlite3.connect(db, timeout=30)
            c.execute("PRAGMA busy_timeout=6000;")
            return c
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay); continue
            raise
    return sqlite3.connect(db, timeout=30)

def _ensure_views_and_tables():
    with _conn(DB) as c:
        c.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS cases(
          id INTEGER PRIMARY KEY,
          name TEXT UNIQUE,
          note TEXT,
          created_utc INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS case_evidence(
          case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
          evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE,
          added_utc INTEGER DEFAULT (strftime('%s','now')),
          PRIMARY KEY (case_id, evidence_id)
        );
        """)
        c.commit()

def _read_watchlist():
    rules=[]
    if not os.path.exists(WATCH): return rules
    for ln in open(WATCH,"r",encoding="utf-8",errors="ignore"):
        ln=ln.strip()
        if not ln or ln.startswith("#"): continue
        parts=[p.strip() for p in re.split(r"\t+| {2,}", ln)]
        if len(parts)<5: parts += [""]*(5-len(parts))
        tag, query, urlfilter, case_name, priority = parts[:5]
        try: priority=int(priority)
        except: priority=0
        rules.append({
            "tag": tag,
            "query": query,
            "urlfilter": urlfilter if urlfilter else "%",
            "case": case_name if case_name else (tag or "General"),
            "priority": priority
        })
    return rules

def _new_urls_since(c, seconds=36*3600):
    cutoff = int(time.time()) - seconds
    cur=c.execute("SELECT url FROM docs WHERE ts_utc>=? ORDER BY ts_utc DESC", (cutoff,))
    return [r[0] for r in cur.fetchall()]

def _case_id(c, name):
    c.execute("INSERT OR IGNORE INTO cases(name) VALUES(?)", (name,))
    c.execute("SELECT id FROM cases WHERE name=?", (name,))
    return c.fetchone()[0]

def _mark_evidence(c, url, page, quote, note, tags, priority):
    now=int(time.time())
    c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc,tags,status,priority)
                 VALUES(?,?,?,?,?,?, 'open', ?)""",
              (url, page, quote, note, now, tags, priority))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def _attach_to_case(c, eid, case_name):
    cid=_case_id(c, case_name)
    c.execute("INSERT OR IGNORE INTO case_evidence(case_id,evidence_id) VALUES(?,?)", (cid, eid))
    return cid

def _today_digest_path():
    return os.path.join(OUTDIR, time.strftime("alert-%Y%m%d.txt"))

def main():
    _ensure_views_and_tables()
    rules=_read_watchlist()
    if not rules:
        print(json.dumps({"ok":True,"added":0,"note":"watchlist empty"}, ensure_ascii=False)); return
    added=0
    lines=[]
    with _conn(DB) as c:
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON;")
        new_urls=set(_new_urls_since(c, seconds=36*3600))
        if not new_urls:
            print(json.dumps({"ok":True,"added":0,"note":"no new URLs"}, ensure_ascii=False)); return
        for rule in rules:
            q=rule["query"].strip()
            if not q: continue
            cur=c.execute("""
              SELECT p.url, p.page_no, substr(p.text,1,400) AS snip, IFNULL(d.title,'') AS title
              FROM pages_fts fts
              JOIN doc_pages p ON p.id=fts.rowid
              JOIN docs d ON d.url=p.url
              WHERE pages_fts MATCH ?
                AND p.url LIKE ?
              ORDER BY length(p.text) ASC
              LIMIT 30
            """,(q, rule["urlfilter"]))
            hits=[dict(r) for r in cur.fetchall() if r["url"] in new_urls]
            for h in hits[:5]:
                quote = re.sub(r"\s+", " ", h["snip"]).strip()
                note  = f"[ALERT:{rule['tag']}] auto from query: {q}"
                eid = _mark_evidence(c, h["url"], int(h["page_no"] or 1), quote, note, rule["tag"], rule["priority"])
                _attach_to_case(c, eid, rule["case"])
                added += 1
                lines.append(f"- [{rule['case']}] p.{h['page_no']} — {h['title'] or '(untitled)'}\n  {h['url']}\n  \"{quote[:240]}\"")
        c.commit()
    if added>0:
        with open(_today_digest_path(),"a",encoding="utf-8") as f:
            f.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} — {added} new alert hit(s) ===\n")
            f.write("\n".join(lines)+"\n\n")
    print(json.dumps({"ok":True,"added":added,"digest":_today_digest_path()}, ensure_ascii=False))

if __name__=="__main__":
    main()
