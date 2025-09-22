#!/data/data/com.termux/files/usr/bin/python3
import os, re, time, json, sqlite3

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

def sent_split(t:str):
    # crude sentence split
    t=re.sub(r"\s+"," ", t or "").strip()
    parts=re.split(r"(?<=[.!?])\s+", t)
    return [p for p in parts if p]

NEWS_HINT=re.compile(r'\b(news|article|whitehouse\.gov|reuters|apnews|bbc|nyt|wsj|foxnews|politico|thehill|time|economist|guardian|telegraph|spectator|nypost|breitbart|aljazeera|rt\.com|ft\.com|bloomberg|axios|semafor|theintercept|propublica)\b', re.I)

def main():
    now=int(time.time())
    cutoff=now-24*3600  # last 24h
    updated=0
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        # ensure table exists
        c.execute("""CREATE TABLE IF NOT EXISTS doc_summaries(
            url TEXT PRIMARY KEY REFERENCES docs(url) ON DELETE CASCADE,
            summary TEXT,
            ts_utc INTEGER
        );""")
        # pick candidates: recent docs that look like news, missing or short summary
        q="""
        SELECT d.url, IFNULL(d.title,''), IFNULL(d.content,''), IFNULL(s.summary,'')
        FROM docs d
        LEFT JOIN doc_summaries s ON s.url=d.url
        WHERE d.ts_utc>=? AND (s.summary IS NULL OR length(s.summary)<120)
          AND (d.url REGEXP '(whitehouse\\.gov|apnews|reuters|bbc|nytimes|wsj|foxnews|politico|thehill|time|economist|guardian|telegraph|spectator|nypost|breitbart|aljazeera|ft\\.com|bloomberg|axios|semafor|theintercept|propublica)'
               OR d.title REGEXP '(News|Update|Statement|Proclamation|Executive|Order|Report)'
               OR ?)
        LIMIT 400;
        """
        # add REGEXP support
        c.create_function("REGEXP", 2, lambda p,x: 1 if re.search(p, x or "", re.I) else 0)
        rows=c.execute(q,(cutoff,0)).fetchall()
        for url,title,content,old in rows:
            text=content if content else ""
            sents=sent_split(text)
            if not sents: continue
            out=[]; tot=0
            for s in sents:
                out.append(s)
                tot+=len(s)
                if tot>700: break
            summary=" ".join(out)[:900]
            c.execute("INSERT OR REPLACE INTO doc_summaries(url,summary,ts_utc) VALUES(?,?,?)",
                      (url, summary, now))
            updated+=1
        c.commit()
    print(json.dumps({"ok":True,"updated":updated}))
if __name__=="__main__": main()
