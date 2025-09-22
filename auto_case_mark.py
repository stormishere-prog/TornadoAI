#!/data/data/com.termux/files/usr/bin/python3
import sys, sqlite3, json, time, argparse, subprocess, os, re

DB="corpus.db"

def migrate():
    subprocess.run(["/data/data/com.termux/files/usr/bin/sh","./safe_run.sh","python3","evidence_migrate.py"],
                   cwd=os.path.dirname(__file__))

def auto_case_name(from_search, url):
    # simple case name heuristic
    if from_search:
        return f"AutoCase: {from_search.strip()[:60]}"
    host = re.sub(r"^https?://","", url).split("/")[0]
    return f"AutoCase: {host}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--page", required=True, type=int)
    ap.add_argument("--quote", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--from-search", default="")
    ap.add_argument("--case", dest="case_name", default="")
    args=ap.parse_args()

    migrate()

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        ts = int(time.time())

        # ensure / pick case
        case_name = args.case_name or auto_case_name(args.from_search, args.url)
        c.execute("INSERT OR IGNORE INTO cases(name, note, created_utc) VALUES(?,?,?)",
                  (case_name, args.from_search or "", ts))
        case_id = c.execute("SELECT id FROM cases WHERE name=?",(case_name,)).fetchone()[0]

        # add evidence
        c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc)
                     VALUES(?,?,?,?,?)""",
                  (args.url, args.page, args.quote, args.note, ts))
        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]

        # copy propaganda fields from page
        row = c.execute("""SELECT propaganda_score, IFNULL(propaganda_tags,'')
                            FROM doc_pages WHERE url=? AND page_no=?""",
                        (args.url, args.page)).fetchone()
        if row:
            score, tags = row[0] or 0.0, row[1] or ""
            c.execute("UPDATE evidence SET propaganda_score=?, propaganda_tags=? WHERE id=?",
                      (float(score), tags, eid))

        # link to case
        c.execute("INSERT OR IGNORE INTO case_evidence(case_id, evidence_id, added_utc) VALUES(?,?,?)",
                  (case_id, eid, ts))

        title = c.execute("SELECT IFNULL(title,'') FROM docs WHERE url=?",(args.url,)).fetchone()
        title = title[0] if title else ""

    print(json.dumps({
        "ok": True,
        "case": case_name,
        "evidence_id": eid,
        "copied_propaganda": bool(row),
        "citation": f"{title} — p.{args.page} — {args.url}"
    }, ensure_ascii=False))

if __name__=="__main__": main()
