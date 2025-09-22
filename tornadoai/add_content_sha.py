#!/data/data/com.termux/files/usr/bin/python3
import os, sqlite3, hashlib, time, json

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

def sha256(text):
    s=(text or "").strip()
    return hashlib.sha256(s.encode("utf-8","ignore")).hexdigest() if s else ""

with sqlite3.connect(DB, timeout=60) as c:
    c.execute("PRAGMA foreign_keys=ON;")

    # 0) Drop any SHA unique indexes so backfill can't collide mid-run
    idxs = c.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='docs' AND sql LIKE '%content_sha%'"
    ).fetchall()
    for (name,) in idxs:
        try: c.execute(f"DROP INDEX IF EXISTS {name}")
        except: pass
    c.commit()

    # 1) Ensure column exists
    has = c.execute("SELECT 1 FROM pragma_table_info('docs') WHERE name='content_sha' LIMIT 1").fetchone()
    if not has:
        c.execute("ALTER TABLE docs ADD COLUMN content_sha TEXT DEFAULT ''")
        c.commit()

    # 2) Backfill content_sha (prefer page 1 body, else docs.content)
    rows = c.execute("""
        SELECT d.rowid, d.url, COALESCE(dp.content, d.content, '') AS body
        FROM docs d
        LEFT JOIN doc_pages dp ON dp.url=d.url AND dp.page_no=1
        WHERE IFNULL(d.content_sha,'')=''
    """).fetchall()

    updated = 0
    for _rowid, url, body in rows:
        h = sha256(body)
        if not h: 
            continue
        cur = c.execute("UPDATE docs SET content_sha=? WHERE url=?", (h, url))
        updated += getattr(cur, "rowcount", 0)
    c.commit()

    # 3) Dedupe: keep the earliest row per SHA, drop the rest
    # (Only applies where content_sha is non-empty)
    cur = c.execute("""
        DELETE FROM docs
        WHERE content_sha<>''
          AND rowid NOT IN (
            SELECT MIN(rowid) FROM docs WHERE content_sha<>'' GROUP BY content_sha
          )
    """)
    deleted = getattr(cur, "rowcount", 0)
    c.commit()

    # 4) Recreate a partial UNIQUE index for future inserts
    c.execute("""
      CREATE UNIQUE INDEX IF NOT EXISTS uq_docs_content_sha
      ON docs(content_sha) WHERE content_sha<>''
    """)
    c.commit()

print(json.dumps({"ok": True, "updated": updated, "deleted_dupes": deleted, "ts": int(time.time())}))
