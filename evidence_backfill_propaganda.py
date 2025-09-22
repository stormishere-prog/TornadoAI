#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, json
DB="corpus.db"

with sqlite3.connect(DB, timeout=30) as c:
    c.execute("PRAGMA foreign_keys=ON;")
    rows = c.execute("""
      SELECT e.id, e.url, e.page_no
      FROM evidence e
      WHERE e.ev_prop_score IS NULL OR e.ev_prop_tags IS NULL OR e.ev_prop_tags='';
    """).fetchall()
    updated = 0
    for eid,url,page in rows:
        row = c.execute("""
          SELECT propaganda_score, propaganda_tags
          FROM doc_pages
          WHERE url=? AND page_no=?
          LIMIT 1
        """,(url,page)).fetchone()
        if row:
            score, tags = row
            c.execute("""
              UPDATE evidence
                 SET ev_prop_score=?, ev_prop_tags=COALESCE(ev_prop_tags,'' ) || CASE WHEN COALESCE(ev_prop_tags,'')='' THEN '' ELSE ',' END || COALESCE(?, '')
               WHERE id=?""", (score, tags or '', eid))
            updated += 1

print(json.dumps({"ok": True, "updated": updated}))
