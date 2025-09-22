#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, argparse, time, json

DB="corpus.db"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",   required=True)
    ap.add_argument("--page",  required=True, type=int)
    ap.add_argument("--quote", required=True)
    ap.add_argument("--note",  default="")
    ap.add_argument("--tags",  default="")        # your manual tags (optional)
    ap.add_argument("--status",default="open")
    ap.add_argument("--priority", type=int, default=0)
    ap.add_argument("--ev-prop-notes", default="") # optional human note about propaganda
    args=ap.parse_args()

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        # pull the current propaganda analysis from the page (if any)
        row = c.execute("""
            SELECT
              COALESCE(propaganda_score, NULL),
              COALESCE(propaganda_tags , '')
            FROM doc_pages
            WHERE url=? AND page_no=?
            LIMIT 1
        """, (args.url, args.page)).fetchone()

        ev_prop_score, ev_prop_tags = (row if row else (None, ""))

        # insert evidence with frozen snapshot fields
        ts = int(time.time())
        c.execute("""
          INSERT INTO evidence(url,page_no,quote,note,tags,status,priority,t_start,t_end,ts_utc,
                               ev_prop_score, ev_prop_tags, ev_prop_notes)
          VALUES(?,?,?,?,?,?,?,NULL,NULL,?, ?, ?, ?)
        """, (args.url, args.page, args.quote, args.note, args.tags, args.status, args.priority, ts,
              ev_prop_score, ev_prop_tags, args.ev_prop_notes))

        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        title = c.execute("SELECT IFNULL(title,'') FROM docs WHERE url=?", (args.url,)).fetchone()
        title = title[0] if title else ""

    print(json.dumps({
      "ok": True,
      "evidence_id": eid,
      "title": title,
      "snapshot": {
         "score": ev_prop_score,
         "tags":  ev_prop_tags
      },
      "citation": f"{title} — p.{args.page} — {args.url}"
    }, ensure_ascii=False))

if __name__=="__main__": main()
