import re
POST_SPLIT = re.compile(r'\n-{3,}\n')

#!/data/data/com.termux/files/usr/bin/python3
import os, re, time, json, sqlite3, urllib.request, html

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
HAND=os.path.join(ROOT,"x_handles.txt")
UA={"User-Agent":"Mozilla/5.0 TornadoAI/1.0"}

def get(url):
    try:
        req=urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8","ignore")
    except Exception:
        return ""

def upsert(c, url, body, ts=None):
    if not url:
        return 0
    t = int(ts or time.time())
    title = (body or '')[:80]
    body = body or ''
    # write only into docs
    c.execute("""INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_tag,doc_type,page_count)
                 VALUES(?,?,?,?,?,?,COALESCE((SELECT page_count FROM docs WHERE url=?),1))""",
              (url, title, body, t, "independent", "x", url))
    return 1

def parse_posts(txt, handle):
    # Keep only the top section; Jina returns a big readable dump
    # Split into chunks by blank lines, keep chunks that mention the handle or look like posts.
    chunks=[c.strip() for c in POST_SPLIT.split(txt) if c.strip()]
    posts=[]
    for ch in chunks:
        if len(ch) < 30: continue
        # Heuristic: lines that start with handle or contain a time marker or a lot of tweet-y punctuation
        if (handle.lower() in ch.lower()) or re.search(r'\b\d{1,2}:\d{2}\s*(AM|PM)\b', ch) or (' / ' in ch and len(ch) > 60):
            posts.append(ch)
    # Return at most 20 newest
    return posts[:20]

def main():
    if not os.path.exists(HAND):
        print(json.dumps({"ok":False,"error":"x_handles.txt missing"})); return
    handles=[l.strip().lstrip("@") for l in open(HAND) if l.strip() and not l.startswith("#")]
    added=0; per={}
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        for h in handles:
            # Jina text proxy of x.com
            url=f"https://r.jina.ai/http://x.com/{h}"
            txt=get(url)
            got=0
            if txt:
                for post in parse_posts(txt, h):
                    got += upsert(c, f"https://x.com/{h}", post, int(time.time()))
            per[h]=got; added+=got
        c.commit()
    print(json.dumps({"ok":True,"added":added,"per_handle":per}))

if __name__=="__main__":
    main()
