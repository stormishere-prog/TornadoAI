# ensure schema is present/up-to-date
import os, sys
sys.path.insert(0, os.path.dirname(__file__) or ".")
import migrate
migrate.ensure(os.path.join(os.path.dirname(__file__) or ".", "corpus.db"))

#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, sys, re, json

DB="corpus.db"
STOP={"the","and","what","did","a","an","to","of","in","on","for","last","cover","about","with","is","are","be"}

def terms_from(q):
    tok=re.findall(r"[a-zA-Z0-9]{2,}", q.lower())
    return [t for t in tok if t not in STOP][:10]

def fts_query_string(q):
    return " ".join(t+"*" for t in terms_from(q))

def like_params(q):
    ts=terms_from(q)
    if not ts: return None, ()
    cond=" OR ".join(["title LIKE ? OR content LIKE ?"]*len(ts))
    args=[]
    for t in ts:
        pat=f"%{t}%"; args+= [pat,pat]
    return cond, tuple(args)

def base_rows(c, q, limit):
    rows=[]
    # FTS
    try:
        ftq=fts_query_string(q)
        if ftq:
            cur=c.execute("""
                SELECT d.url, IFNULL(d.title,''), substr(IFNULL(d.content,''),1,400) AS snippet, d.ts_utc
                FROM docs d JOIN docs_fts f ON f.rowid=d.rowid
                WHERE f MATCH ?
                ORDER BY d.ts_utc DESC LIMIT ?;
            """, (ftq, limit*4))
            rows=cur.fetchall()
    except sqlite3.OperationalError:
        rows=[]
    # LIKE fallback / augment
    if len(rows)<limit:
        cond,args=like_params(q)
        if cond:
            cur=c.execute(f"""
                SELECT url, IFNULL(title,''), substr(IFNULL(content,''),1,400) AS snippet, ts_utc
                FROM docs
                WHERE {cond}
                ORDER BY ts_utc DESC LIMIT ?;
            """, args+(limit*4,))
            rows += cur.fetchall()
    return rows

def rerank(rows, govonly=False):
    scored=[]
    for (u,t,s,ts) in rows:
        score=0
        ul=u.lower()
        # source quality
        if "whitehouse.gov/presidential-actions" in ul: score+=80
        elif ul.endswith(".gov/") or ".gov/" in ul:     score+=40
        elif "congress.gov" in ul or "justice.gov" in ul: score+=35
        # penalize non-official
        if ul.startswith("file://"): score-=60
        # recency nudge
        try: score += int(ts or 0)/1e12  # tiny tie-break
        except: pass
        if govonly and (".gov" not in ul and "whitehouse.gov" not in ul):
            continue
        scored.append((score,u,t,s,ts))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [(u,t,s) for (_,u,t,s,_) in scored]

def main():
    # flags: --govonly, --max N
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    flags=[a for a in sys.argv[1:] if a.startswith("--")]
    govonly = any(f=="--govonly" for f in flags)
    maxn=5
    for f in flags:
        if f.startswith("--max"):
            try: maxn=int(f.split("=",1)[1])
            except: pass

    q=" ".join(args).strip() or sys.stdin.read().strip()
    if not q:
        print(json.dumps({"error":"empty question"})); return
    with sqlite3.connect(DB) as c:
        raw=base_rows(c,q,maxn)
    rows=rerank(raw, govonly=govonly)[:maxn]

    conf=min(99, 30+10*len(rows))
    label="FACT" if conf>=90 else "GUESS"
    bullets="\n".join([f"• {t or '(untitled)'} — {u}\n  {s}" for (u,t,s) in rows]) if rows else "• No local hits."
    answer=f"{label} — {conf}% confidence.\n{bullets}"
    print(json.dumps({
        "answer":answer,
        "confidence":conf,
        "label":label,
        "citations":[{"url":u,"title":t} for (u,t,_) in rows]
    }, ensure_ascii=False))

if __name__=="__main__":
    main()
