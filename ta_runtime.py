import os, time, json, sqlite3, subprocess, sys

def _conn(db):
    delay=0.2
    for _ in range(8):
        try:
            c = sqlite3.connect(db, timeout=30)
            c.execute("PRAGMA busy_timeout=6000;")
            return c
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                time.sleep(delay); delay=min(delay*1.8,3.0)
                continue
            raise
    return sqlite3.connect(db, timeout=30)


ROOT = os.path.dirname(__file__) or "."
DB   = os.path.join(ROOT, "corpus.db")
PYEXE = sys.executable or "python3"

def _ensure_schema():
    # core migrate
    try:
        import migrate
        migrate.ensure(DB)
    except Exception:
        subprocess.run([PYEXE, os.path.join(ROOT, "migrate.py")], check=False)

    # evidence/cases/views (idempotent; ignore dup column errors)
    ddl = """
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS evidence(
      id INTEGER PRIMARY KEY,
      url TEXT REFERENCES docs(url) ON DELETE CASCADE,
      page_no INTEGER,
      quote TEXT,
      note TEXT,
      ts_utc INTEGER DEFAULT (strftime('%s','now'))
    );
    BEGIN;
    """  # we’ll append ALTERs below, catching duplicates
    with _conn(DB) as c:
        c.isolation_level = None
        c.executescript(ddl)
        for alter in [
            "ALTER TABLE evidence ADD COLUMN tags TEXT DEFAULT ''",
            "ALTER TABLE evidence ADD COLUMN status TEXT DEFAULT 'open'",
            "ALTER TABLE evidence ADD COLUMN priority INTEGER DEFAULT 0",
            "ALTER TABLE evidence ADD COLUMN t_start REAL DEFAULT NULL",
            "ALTER TABLE evidence ADD COLUMN t_end   REAL DEFAULT NULL",
        ]:
            try: c.execute(alter)
            except sqlite3.OperationalError as e:
                # duplicate column name – safe to ignore
                if "duplicate column name" not in str(e).lower(): raise
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
        DROP VIEW IF EXISTS v_evidence_full;
        CREATE VIEW v_evidence_full AS
        SELECT e.id, e.url, e.page_no, e.quote, e.note, e.tags, e.status, e.priority,
               e.t_start, e.t_end, e.ts_utc,
               IFNULL(d.title,'') AS title,
               d.page_count,
               d.sha256 AS doc_sha256
        FROM evidence e
        LEFT JOIN docs d ON d.url = e.url;

        DROP VIEW IF EXISTS v_case_bundle;
        CREATE VIEW v_case_bundle AS
        SELECT c.name AS case_name, e.*
        FROM v_evidence_full e
        JOIN case_evidence ce ON ce.evidence_id=e.id
        JOIN cases c ON c.id=ce.case_id
        ORDER BY c.name, e.ts_utc;
        """)

_ensure_schema()

def harvest_daily_pdfs(limit_items=120, limit_pdfs=400, list_pages=10):
    subprocess.run(
        [PYEXE, os.path.join(ROOT, "foia_deep.py"),
         "--limit-items", str(limit_items),
         "--limit-pdfs",  str(limit_pdfs),
         "--list-pages",  str(list_pages)],
        check=False
    )
    subprocess.run([PYEXE, os.path.join(ROOT, "fetch_and_ingest.py")], check=False)
    return {"ok": True}

def harvest_weekly_media():
    subprocess.run(
        [PYEXE, os.path.join(ROOT, "foia_deep.py"),
         "--limit-items", "200", "--limit-pdfs", "600", "--list-pages", "15"],
        check=False
    )
    subprocess.run([PYEXE, os.path.join(ROOT, "fetch_and_ingest.py")], check=False)
    return {"ok": True}

def nightly_tick(window_start_hour=2, window_end_hour=3, video_weekday="Sun",
                 daily_stamp=os.path.join(ROOT, ".daily_foia_ran"),
                 weekly_stamp=os.path.join(ROOT, ".weekly_media_ran")):
    _ensure_schema()
    now = time.localtime()
    hour = now.tm_hour
    in_window = (window_start_hour <= hour <= window_end_hour)
    ran = {"daily": False, "weekly": False}

    def _is_today(path):
        try:
            ts = int(open(path).read().strip()); t = time.localtime(ts)
            return time.strftime("%Y-%m-%d", t) == time.strftime("%Y-%m-%d", now)
        except Exception: return False

    def _is_this_week(path):
        try:
            ts = int(open(path).read().strip()); t = time.localtime(ts)
            return time.strftime("%G-%V", t) == time.strftime("%G-%V", now)
        except Exception: return False

    if in_window:
        if not _is_today(daily_stamp):
            harvest_daily_pdfs()
            open(daily_stamp, "w").write(str(int(time.time())))
            ran["daily"] = True
        weekday = time.strftime("%a", now)  # Sun/Mon/...
        if weekday == video_weekday and not _is_this_week(weekly_stamp):
            harvest_weekly_media()
            open(weekly_stamp, "w").write(str(int(time.time())))
            ran["weekly"] = True

    return {"ok": True, "in_window": in_window, **ran}

def search_pages(query:str, urlfilter:str="", limit:int=5):
    sql = """
    SELECT p.url, p.page_no, substr(p.text,1,500) AS snippet, d.title
    FROM pages_fts f
    JOIN doc_pages p ON p.id=f.rowid
    JOIN docs d ON d.url=p.url
    WHERE pages_fts MATCH ?
    {and_url}
    ORDER BY length(p.text) ASC
    LIMIT ?
    """
    and_url = "AND p.url LIKE ?" if urlfilter else ""
    with _conn(DB) as c:
        c.row_factory = sqlite3.Row
        if urlfilter:
            rows = c.execute(sql.format(and_url=and_url), (query, urlfilter, limit)).fetchall()
        else:
            rows = c.execute(sql.format(and_url=""), (query, limit)).fetchall()
    return [dict(title=r["title"] or "(untitled)", url=r["url"], page=int(r["page_no"] or 1), snippet=r["snippet"] or "") for r in rows]

def add_evidence(url, page, quote, note="", tags="", status="open", priority=0, t_start=None, t_end=None):
    with _conn(DB) as c:
        c.execute("""INSERT INTO evidence(url,page_no,quote,note,tags,status,priority,t_start,t_end,ts_utc)
                     VALUES(?,?,?,?,?,?,?,?,?,strftime('%s','now'))""",
                  (url, page, quote, note, tags, status, priority, t_start, t_end))
        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        title = c.execute("SELECT IFNULL(title,'') FROM docs WHERE url=?", (url,)).fetchone()
    return {"ok": True, "evidence_id": eid, "title": (title and title[0]) or ""}

def create_case(name, note=""):
    with _conn(DB) as c:
        c.execute("INSERT OR IGNORE INTO cases(name,note) VALUES(?,?)", (name, note))
        cid = c.execute("SELECT id FROM cases WHERE name=?", (name,)).fetchone()[0]
    return {"ok": True, "case_id": cid}

def attach_evidence(case_id, evidence_id):
    with _conn(DB) as c:
        c.execute("""INSERT OR IGNORE INTO case_evidence(case_id,evidence_id,added_utc)
                     VALUES(?,?,strftime('%s','now'))""", (case_id, evidence_id))
    return {"ok": True}
