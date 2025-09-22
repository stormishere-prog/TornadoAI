#!/data/data/com.termux/files/usr/bin/python3
import os, sys, re, json, sqlite3, argparse, time

DB="corpus.db"

def search(c, q, urlfilter, limit):
    if urlfilter and urlfilter != "%":
        cur=c.execute("""
            SELECT p.url, p.page_no, substr(p.text,1,500) AS snip, d.title
            FROM pages_fts f
            JOIN doc_pages p ON p.id=f.rowid
            JOIN docs d ON d.url=p.url
            WHERE pages_fts MATCH ? AND p.url LIKE ?
            ORDER BY length(p.text) ASC
            LIMIT ?""",(q, urlfilter, limit))
    else:
        cur=c.execute("""
            SELECT p.url, p.page_no, substr(p.text,1,500) AS snip, d.title
            FROM pages_fts f
            JOIN doc_pages p ON p.id=f.rowid
            JOIN docs d ON d.url=p.url
            WHERE pages_fts MATCH ?
            ORDER BY length(p.text) ASC
            LIMIT ?""",(q, limit))
    rows=cur.fetchall()
    out=[]
    for r in rows:
        out.append({
            "title": r[3] or "(untitled)",
            "url": r[0],
            "page": int(r[1] or 1),
            "snippet": (r[2] or "").replace("\n"," ")
        })
    return out

def ensure_case(c, name):
    if not name: return None
    c.execute("INSERT OR IGNORE INTO cases(name) VALUES(?)",(name,))
    cid=c.execute("SELECT id FROM cases WHERE name=?",(name,)).fetchone()
    return cid[0] if cid else None

def mark(c, url, page, quote, note, case_name=None, tags="", priority=0):
    # insert evidence
    ts=int(time.time())
    c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc,t_start,t_end,tags,priority,status)
                 VALUES(?,?,?,?,?,NULL,NULL,?,?,'open')""",
              (url, page, quote, note, ts, tags, priority))
    eid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    # attach to case if provided
    if case_name:
        cid=ensure_case(c, case_name)
        if cid:
            c.execute("""INSERT OR IGNORE INTO case_evidence(case_id,evidence_id)
                         VALUES(?,?)""",(cid,eid))
    return eid

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("question", nargs="+", help="what do you want to find?")
    ap.add_argument("--urlfilter", default="%", help="SQL LIKE filter for URL (default: all)")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--auto-mark", action="store_true", help="mark the first hit as evidence")
    ap.add_argument("--case", default="", help="case name to attach if marking")
    ap.add_argument("--note", default="", help="note to store if marking")
    ap.add_argument("--tags", default="", help="comma tags for evidence")
    ap.add_argument("--priority", type=int, default=0)
    args=ap.parse_args()

    q=" ".join(args.question).strip()
    if not q:
        print(json.dumps({"ok":False,"error":"empty question"})); return

    with sqlite3.connect(DB) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        hits=search(c, q, args.urlfilter, args.limit)

        result={"ok":True,"query":q,"hits":hits}
        if args.auto_mark and hits:
            h=hits[0]
            eid=mark(c, h["url"], h["page"], h["snippet"], args.note or q,
                     case_name=(args.case or None),
                     tags=args.tags, priority=args.priority)
            result["marked"]={"evidence_id":eid, "url":h["url"], "page":h["page"]}

        print(json.dumps(result, ensure_ascii=False))

if __name__=="__main__":
    main()
