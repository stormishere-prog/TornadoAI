#!/data/data/com.termux/files/usr/bin/python3
import sys, json, sqlite3, argparse, time

DB="corpus.db"

def main():
    ap=argparse.ArgumentParser(description="Quick search over pages_fts with optional auto-mark of first hit.")
    ap.add_argument("query", nargs="+", help="FTS5 query")
    ap.add_argument("--urlfilter", default="%", help="SQL LIKE filter for URL (default: % = all)")
    ap.add_argument("--limit", type=int, default=5, help="max hits (default 5)")
    ap.add_argument("--mark-first", action="store_true", help="insert first hit as evidence")
    ap.add_argument("--case", default="", help="case name when marking")
    ap.add_argument("--note", default="", help="note to store on evidence when marking")
    args=ap.parse_args()

    q=" ".join(args.query).strip()
    out={"ok":True,"hits":[]}

    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        # search
        cur=c.execute("""
            SELECT p.url, p.page_no AS page, substr(p.text,1,500) AS snippet,
                   IFNULL(d.title,'') AS title
            FROM pages_fts f
            JOIN doc_pages p ON p.id=f.rowid
            JOIN docs d ON d.url=p.url
            WHERE pages_fts MATCH ? AND p.url LIKE ?
            ORDER BY length(p.text) ASC
            LIMIT ?
        """,(q, args.urlfilter, args.limit))
        rows=cur.fetchall()
        for r in rows:
            out["hits"].append({
                "title": r["title"] or "(untitled)",
                "url": r["url"],
                "page": int(r["page"] or 1),
                "snippet": (r["snippet"] or "").replace("\n"," ")
            })

        # optional mark of first hit
        if args["mark_first"] if isinstance(args, dict) else args.mark_first:
            if not out["hits"]:
                print(json.dumps({**out,"marked":False,"reason":"no hits"})); return
            hit=out["hits"][0]
            # ensure doc exists (FK safety)
            chk=c.execute("SELECT 1 FROM docs WHERE url=?",(hit["url"],)).fetchone()
            if not chk:
                print(json.dumps({**out,"marked":False,"reason":"doc missing"})); return
            c.execute("""
                INSERT INTO evidence(url,page_no,quote,note,ts_utc)
                VALUES(?,?,?,?,?)
            """,(hit["url"], hit["page"], hit["snippet"], args.note, int(time.time())))
            evid=c.execute("SELECT last_insert_rowid()").fetchone()[0]

            case_name = args.case.strip() or q
            c.execute("INSERT OR IGNORE INTO cases(name) VALUES(?)",(case_name,))
            cid = c.execute("SELECT id FROM cases WHERE name=?",(case_name,)).fetchone()[0]
            c.execute("""
                INSERT OR IGNORE INTO case_evidence(case_id,evidence_id)
                VALUES(?,?)
            """,(cid, evid))
            out["marked"]=True
            out["evidence_id"]=evid
            out["case"]=case_name

    print(json.dumps(out, ensure_ascii=False))

if __name__=="__main__": main()
