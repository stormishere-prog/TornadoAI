#!/data/data/com.termux/files/usr/bin/python3
import os, json, sqlite3, time, hashlib

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
WL=os.path.join(ROOT,"watchlist_truth.txt")

def sha256(txt): return hashlib.sha256(txt.encode("utf-8","ignore")).hexdigest()

def ingest(handle, posts):
    now=int(time.time())
    with sqlite3.connect(DB, timeout=30) as c:
        for post in posts:
            url=post["url"]; txt=post["text"]; ts=post.get("ts",now)
            h=sha256(txt)
            c.execute("""INSERT OR IGNORE INTO docs(url,title,content,ts_utc,source_trust,sha256)
                         VALUES(?,?,?,?,?,?)""",
                      (url, f"Truth post by {handle}", txt, ts, "official", h))
        c.commit()

def fetch(handle):
    # placeholder: expects truth_posts.json (you can fill manually or scrape separately)
    path=os.path.join(ROOT,"truth_posts.json")
    if not os.path.exists(path): return []
    data=json.load(open(path))
    return data.get(handle,[])

def main():
    if not os.path.exists(WL): return
    with open(WL) as f:
        handles=[ln.strip() for ln in f if ln.strip()]
    for h in handles:
        posts=fetch(h)
        ingest(h,posts)
    print(json.dumps({"ok":True,"handles":handles}))

if __name__=="__main__":
    main()
