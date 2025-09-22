#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, sqlite3, hashlib, requests

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
WL=os.path.join(ROOT,"watchlist_x.txt")

def sha256(txt): return hashlib.sha256(txt.encode("utf-8","ignore")).hexdigest()

def ingest(handle, posts):
    now=int(time.time())
    with sqlite3.connect(DB, timeout=30) as c:
        for post in posts:
            url=post["url"]; txt=post["text"]; ts=post.get("ts",now)
            h=sha256(txt)
            c.execute("""INSERT OR IGNORE INTO docs(url,title,content,ts_utc,source_trust,sha256)
                         VALUES(?,?,?,?,?,?)""",
                      (url, f"X post by {handle}", txt, ts, "independent", h))
        c.commit()

def fetch(handle):
    # use nitter as a light scraper (public)
    url=f"https://nitter.net/{handle}"
    try:
        r=requests.get(url, timeout=15)
        if r.status_code!=200: return []
        posts=[]
        for line in r.text.splitlines():
            if "tweet-content media-body" in line or "tweet-content" in line:
                text=line.strip()
                posts.append({"url":url, "text":text})
        return posts[:5]
    except Exception as e:
        return []

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
