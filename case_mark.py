#!/data/data/com.termux/files/usr/bin/python3
import os, sys, json, time, re, hashlib, sqlite3, subprocess, argparse, shlex

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")

def _conn(db):
    delay=0.2
    for _ in range(8):
        try:
            c=sqlite3.connect(db, timeout=30)
            c.execute("PRAGMA busy_timeout=6000;")
            c.execute("PRAGMA foreign_keys=ON;")
            return c
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay); delay=min(delay*1.8, 3.0)
                continue
            raise
    return sqlite3.connect(db, timeout=30)

def _ensure_schema(c):
    # minimal ensures; your DB already has most of this
    c.executescript("""
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
    # columns on evidence (no-op if they already exist)
    cols = {r[1] for r in c.execute("PRAGMA table_info(evidence)")}
    if "tags" not in cols:      c.execute("ALTER TABLE evidence ADD COLUMN tags TEXT DEFAULT ''")
    if "status" not in cols:    c.execute("ALTER TABLE evidence ADD COLUMN status TEXT DEFAULT 'open'")
    if "priority" not in cols:  c.execute("ALTER TABLE evidence ADD COLUMN priority INTEGER DEFAULT 0")
    if "t_start" not in cols:   c.execute("ALTER TABLE evidence ADD COLUMN t_start REAL")
    if "t_end" not in cols:     c.execute("ALTER TABLE evidence ADD COLUMN t_end REAL")
    if "doc_sha256" not in cols:c.execute("ALTER TABLE evidence ADD COLUMN doc_sha256 TEXT")

    # docs.sha256 (no-op if exists)
    dcols = {r[1] for r in c.execute("PRAGMA table_info(docs)")}
    if "sha256" not in dcols: c.execute("ALTER TABLE docs ADD COLUMN sha256 TEXT")

def _sha(s:str)->str: return hashlib.sha256(s.encode("utf-8","ignore")).hexdigest()

def _auto_tags_and_priority(title:str, url:str, snippet:str):
    text = " ".join([title or "", url or "", snippet or ""]).lower()
    tags = set()
    score = 0
    # quick heuristics
    if "executive order" in text or "it is hereby ordered" in text: tags.add("executive-order"); score += 2
    if "section 702" in text or "foreign intelligence" in text or "fisa" in text: tags.add("702"); tags.add("fisa"); score += 3
    if "unmasking" in text or "minimization" in text: tags.add("surveillance"); score += 2
    if "cia.gov/readingroom" in url: tags.add("cia")
    if "dni.gov" in url: tags.add("dni")
    if "nsa.gov" in url: tags.add("nsa")
    if "vault.fbi.gov" in url or "fbi.gov" in url: tags.add("fbi")
    if "justice.gov" in url: tags.add("doj")
    if "pdf" in url: tags.add("pdf")
    # bump for gov sources
    if re.search(r"https://(www\.)?(whitehouse\.gov|justice\.gov|dni\.gov|cia\.gov|nsa\.gov|fbi\.gov|archives\.gov)", url):
        score += 2
    # length/quality bump
    if snippet and len(snippet) > 280: score += 1
    priority = 3 if score >= 6 else 2 if score >= 3 else 1
    return ",".join(sorted(tags)), priority

def _ensure_case(c, case_name:str)->int:
    row = c.execute("SELECT id FROM cases WHERE name=?", (case_name,)).fetchone()
    if row: return int(row[0])
    c.execute("INSERT INTO cases(name) VALUES(?)", (case_name,))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def _dedupe_exists(c, url, page_no, quote):
    h = _sha(f"{url}::{page_no}::{quote}")
    row = c.execute("SELECT id FROM evidence WHERE url=? AND page_no=? AND quote=?",
                    (url, page_no, quote)).fetchone()
    return (True, row[0]) if row else (False, None)

def _doc_sha(c, url):
    row = c.execute("SELECT sha256 FROM docs WHERE url=?", (url,)).fetchone()
    return row[0] if row and row[0] else None

def _insert_evidence(c, url, page_no, quote, note, tags, priority, t_start=None, t_end=None):
    c.execute("""INSERT INTO evidence(url,page_no,quote,note,tags,status,priority,t_start,t_end,ts_utc,doc_sha256)
                 VALUES(?,?,?,?,?,'open',?,?,?,strftime('%s','now'),?)""",
              (url, page_no, quote, note or "", tags or "", int(priority),
               t_start, t_end, _doc_sha(c, url)))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def _link_case(c, case_id, evidence_id):
    c.execute("INSERT OR IGNORE INTO case_evidence(case_id, evidence_id) VALUES(?,?)",
              (case_id, evidence_id))

def _search(query, urlfilter=None, limit=10):
    cmd = ["python3", os.path.join(ROOT, "search_pages.py")] + shlex.split(query)
    if urlfilter: cmd += ["--urlfilter", urlfilter]
    cmd += ["--limit", str(limit)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "search failed")
    return json.loads(p.stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="case name to file under")
    ap.add_argument("--from-search", help="query terms (the script will run search_pages.py)")
    ap.add_argument("--urlfilter", default="", help="optional LIKE filter for URL (e.g. https://www.justice.gov/% )")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--hit-json", help="single hit JSON (title,url,page,snippet)")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    with _conn(DB) as c:
        _ensure_schema(c)
        c.execute("BEGIN IMMEDIATE;")
        try:
            case_id = _ensure_case(c, args.case)

            hits = []
            if args.hit_json:
                hits = [json.loads(args.hit_json)]
            elif args.from-search:
                res = _search(args.from_search, args.urlfilter or None, args.limit)
                hits = res.get("hits", [])
            else:
                raise SystemExit("Provide --from-search or --hit-json")

            filed = []
            for h in hits:
                url   = h.get("url","")
                page  = int(h.get("page") or 1)
                snip  = (h.get("snippet") or "").strip()
                title = h.get("title") or ""
                if not url or not snip:
                    continue
                # dedupe
                exists, eid = _dedupe_exists(c, url, page, snip)
                if not exists:
                    tags, prio = _auto_tags_and_priority(title, url, snip)
                    eid = _insert_evidence(c, url, page, snip, args.note, tags, prio)
                _link_case(c, case_id, eid)
                filed.append({"evidence_id": eid, "url": url, "page": page})

            c.execute("COMMIT;")
            print(json.dumps({"ok": True, "filed": filed}, ensure_ascii=False))
        except Exception as e:
            c.execute("ROLLBACK;")
            print(json.dumps({"ok": False, "error": str(e)}))
            raise

if __name__ == "__main__":
    main()
