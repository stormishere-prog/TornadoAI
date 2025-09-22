#!/data/data/com.termux/files/usr/bin/python3
import os, sys, json, sqlite3, argparse, time

DB="corpus.db"
ALERTDIR="alerts"
CFG="standing_queries.jsonl"

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
    out=[]
    for url,page,snip,title in cur.fetchall():
        out.append({"url":url,"page":int(page or 1),"snippet":(snip or "").replace("\n"," "), "title":title or ""})
    return out

def evidence_exists(c, url, page):
    r=c.execute("SELECT 1 FROM evidence WHERE url=? AND page_no=? LIMIT 1",(url,page)).fetchone()
    return bool(r)

def ensure_case(c, name):
    c.execute("INSERT OR IGNORE INTO cases(name) VALUES(?)",(name,))
    r=c.execute("SELECT id FROM cases WHERE name=?",(name,)).fetchone()
    return r[0] if r else None

def insert_evidence(c, hit, note, tags, priority, case_name=None):
    ts=int(time.time())
    c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc,t_start,t_end,tags,priority,status)
                 VALUES(?,?,?,?,?,NULL,NULL,?,?,'open')""",
              (hit["url"], hit["page"], hit["snippet"], note, ts, tags, priority))
    eid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    if case_name:
        cid=ensure_case(c, case_name)
        if cid:
            c.execute("INSERT OR IGNORE INTO case_evidence(case_id,evidence_id) VALUES(?,?)",(cid,eid))
    return eid

def load_cfg(path):
    items=[]
    if not os.path.exists(path): return items
    for ln in open(path,"r",encoding="utf-8",errors="ignore"):
        ln=ln.strip()
        if not ln: continue
        items.append(json.loads(ln))
    return items

def log_alert(tag, case, priority, hit, query, outdir):
    os.makedirs(outdir, exist_ok=True)
    line={
        "ts": int(time.time()),
        "tag": tag,
        "case": case,
        "priority": priority,
        "url": hit["url"],
        "page": hit["page"],
        "query": query,
        "snippet": hit["snippet"][:500]
    }
    with open(os.path.join(outdir,"standing.log"),"a",encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False)+"\n")
    return line

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cfg", default=CFG)
    ap.add_argument("--alerts", default=ALERTDIR)
    ap.add_argument("--max-per-tag", type=int, default=1, dest="max_per_tag")
    args=ap.parse_args()

    cfg=load_cfg(args.cfg)
    added=[]
    with sqlite3.connect(DB) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        for item in cfg:
            tag=item.get("tag","")
            q=item.get("query","").strip()
            urlfilter=item.get("urlfilter","%")
            case=item.get("case") or ""
            priority=int(item.get("priority",0))
            note=item.get("note") or q
            tags=item.get("tags","")
            limit=int(item.get("limit",3))
            if not q: continue

            hits=search(c, q, urlfilter, limit)
            taken=0
            for h in hits:
                if evidence_exists(c, h["url"], h["page"]):
                    continue
                eid=insert_evidence(c, h, note, tags, priority, case_name=(case or None))
                alert=log_alert(tag, case or "", priority, h, q, args.alerts)
                alert["evidence_id"]=eid
                added.append(alert)
                taken+=1
                if taken >= args.max_per_tag:
                    break

    print(json.dumps({"ok":True, "added":added}, ensure_ascii=False))

if __name__=="__main__":
    main()
