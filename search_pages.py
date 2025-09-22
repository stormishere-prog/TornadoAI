#!/data/data/com.termux/files/usr/bin/python3
import sys, re, json, sqlite3, argparse
DB="corpus.db"

def to_fts(q:str)->str:
    # strip quotes and collapse to simple boolean-ish terms
    q = re.sub(r'["\']', ' ', q or '')
    terms = re.findall(r'\w{2,}', q.lower())[:12]
    return " ".join(terms)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--urlfilter", default="")
    args=ap.parse_args()

    ftq = to_fts(" ".join(args.query))
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        if args.urlfilter:
            cur=c.execute("""
SELECT p.url, p.page_no, substr(p.text,1,500) AS snip, d.title
FROM pages_fts f
JOIN doc_pages p ON p.id=f.rowid
JOIN docs d ON d.url=p.url
WHERE pages_fts MATCH ? AND p.url LIKE ?
ORDER BY length(p.text) ASC
LIMIT ?""",(ftq, args.urlfilter, args.limit))
        else:
            cur=c.execute("""
SELECT p.url, p.page_no, substr(p.text,1,500) AS snip, d.title
FROM pages_fts f
JOIN doc_pages p ON p.id=f.rowid
JOIN docs d ON d.url=p.url
WHERE pages_fts MATCH ?
ORDER BY length(p.text) ASC
LIMIT ?""",(ftq, args.limit))
        rows=cur.fetchall()

    out=[]
    for r in rows:
        out.append({
            "title": r["title"] or "(untitled)",
            "url": r["url"],
            "page": int(r["page_no"] or 1),
            "snippet": r["snip"] or ""
        })
    print(json.dumps({"hits":out}, ensure_ascii=False))
if __name__=="__main__": main()
