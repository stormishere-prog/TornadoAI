#!/data/data/com.termux/files/usr/bin/python3
import sys, sqlite3, json, time, argparse, subprocess, os

DB="corpus.db"

def migrate():
    # run the small migrator (idempotent)
    p = subprocess.run(["/data/data/com.termux/files/usr/bin/sh","./safe_run.sh","python3","evidence_migrate.py"],
                       cwd=os.path.dirname(__file__), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # ignore output on success; this keeps mark_evidence quiet

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",   required=True)
    ap.add_argument("--page",  required=True, type=int)
    ap.add_argument("--quote", required=True)
    ap.add_argument("--note",  default="")
    args=ap.parse_args()

    migrate()

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        ts = int(time.time())
        # 1) insert base evidence
        c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc)
                     VALUES(?,?,?,?,?)""",
                  (args.url, args.page, args.quote, args.note, ts))
        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 2) copy propaganda fields from the page if available
        row = c.execute("""SELECT propaganda_score, IFNULL(propaganda_tags,'')
                            FROM doc_pages
                           WHERE url=? AND page_no=?""",
                        (args.url, args.page)).fetchone()
        if row:
            score, tags = row[0] or 0.0, row[1] or ""
            c.execute("""UPDATE evidence
                           SET propaganda_score=?, propaganda_tags=?
                         WHERE id=?""",
                      (float(score), tags, eid))

        title = c.execute("SELECT IFNULL(title,'') FROM docs WHERE url=?",(args.url,)).fetchone()
        title = title[0] if title else ""

    print(json.dumps({
        "ok": True,
        "evidence_id": eid,
        "title": title,
        "copied_propaganda": bool(row),
        "citation": f"{title} — p.{args.page} — {args.url}"
    }, ensure_ascii=False))

if __name__=="__main__": main()
