#!/data/data/com.termux/files/usr/bin/python3
import os, time, re, json, sqlite3, urllib.request, urllib.error, xml.etree.ElementTree as ET

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
INST=os.path.join(ROOT,"nitter_instances.txt")
HAND=os.path.join(ROOT,"x_handles.txt")
UA={"User-Agent":"Mozilla/5.0 TornadoAI/1.0"}

def fetch(url, delay=0.0):
    req=urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if delay: time.sleep(delay)
            return r.read()
    except Exception:
        return b""

def upsert(c, url, title, body, ts=None):
    if not url: return 0
    t=int(ts or time.time())
    title=title or ""
    body=body or ""
    # doc_type='x' so we can filter later
    c.execute("""INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_tag,doc_type,page_count)
                 VALUES(?,?,?,?,?,?,COALESCE((SELECT page_count FROM docs WHERE url=?),1))""",
              (url, title, body, t, "independent", "x", url))
    # store first page copy
    c.execute("""INSERT OR REPLACE INTO doc_pages(url,page_no,content)
                 VALUES(?,?,?)""",(url,1,body))
    return 1

def main():
    if not os.path.exists(HAND): print(json.dumps({"ok":False,"error":"x_handles.txt missing"})); return
    inst = [l.strip().rstrip("/") for l in open(INST) if l.strip() and not l.startswith("#")] if os.path.exists(INST) else ["https://nitter.net"]
    handles = [l.strip().lstrip("@") for l in open(HAND) if l.strip() and not l.startswith("#")]
    added=0; per={}
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        for h in handles:
            got=0
            for base in inst:
                rss=f"{base}/{h}/rss"
                xmlb=fetch(rss, delay=2.0)
                if not xmlb: continue
                try:
                    root=ET.fromstring(xmlb)
                except Exception:
                    continue
                for item in root.findall(".//item"):
                    link=item.findtext("link") or ""
                    title=item.findtext("title") or ""
                    desc=item.findtext("description") or ""
                    # crude timestamp parse from pubDate if present
                    pub=item.findtext("{http://purl.org/dc/elements/1.1/}date") or item.findtext("pubDate") or ""
                    ts=int(time.time())
                    upsert(c, link, title, desc, ts)
                    added+=1; got+=1
                if got: break
            per[h]=got
        c.commit()
    print(json.dumps({"ok":True,"added":added,"per_handle":per}))

if __name__=="__main__": main()
