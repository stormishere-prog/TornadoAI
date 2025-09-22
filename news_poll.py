#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, hashlib, urllib.request, urllib.error, xml.etree.ElementTree as ET

ROOT  = "/storage/emulated/0/Download/TornadoAI"
FEEDS = os.path.join(ROOT, "feeds_news.txt")
QUEUE = os.path.join(ROOT, "news_queue.txt")      # tab: url <TAB> feed <TAB> ts
STATE = os.path.join(ROOT, "news_state.json")     # etag/last-modified + seen hashes
SOURCES = os.path.join(ROOT, "sources.txt")
BLOCKLIST = os.path.join(ROOT, "news_blocklist.txt")

MAX_PER_FEED = int(os.environ.get("MAX_NEW_PER_FEED_PER_HOUR", "5"))
GLOBAL_CAP   = int(os.environ.get("HOURLY_GLOBAL_CAP", "60"))
UA = {"User-Agent":"Mozilla/5.0 TornadoAI/1.0"}

def _load_lines(path):
    s=set()
    if os.path.exists(path):
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            for ln in f:
                ln=ln.strip()
                if ln and not ln.startswith("#"): s.add(ln.split("\t",1)[0])
    return s

def _load_block():
    out=[]
    if os.path.exists(BLOCKLIST):
        with open(BLOCKLIST,"r",encoding="utf-8",errors="ignore") as f:
            for ln in f:
                ln=ln.strip()
                if ln and not ln.startswith("#"): out.append(ln.lower())
    return out

def _blocked(u, bl):
    lu=(u or "").lower()
    for p in bl:
        if p in lu:
            return True
    return False

def _load_state():
    if os.path.exists(STATE):
        try: return json.load(open(STATE,"r",encoding="utf-8"))
        except: pass
    return {"feeds":{}, "seen":{}}

def _save_state(st):
    tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(st,f,ensure_ascii=False,indent=2)
    os.replace(tmp,STATE)

def _hash(u): return hashlib.sha1((u or "").encode("utf-8","ignore")).hexdigest()[:16]

def _fetch(url, etag=None, lm=None):
    hdrs=dict(UA)
    if etag: hdrs["If-None-Match"]=etag
    if lm:   hdrs["If-Modified-Since"]=lm
    req=urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data=r.read()
            meta={"etag": r.headers.get("ETag",""), "lm": r.headers.get("Last-Modified","")}
            return 200, data, meta
    except urllib.error.HTTPError as e:
        if e.code==304: return 304, b"", {}
        return e.code, b"", {}
    except Exception:
        return -1, b"", {}

def _parse_links(feed_bytes):
    out=[]
    try:
        root=ET.fromstring(feed_bytes)
        # RSS <item>
        for item in root.findall(".//item"):
            link=item.findtext("link") or item.findtext("{http://purl.org/rss/1.0/}link") or ""
            guid=item.findtext("guid") or ""
            out.append((link.strip() or guid.strip()))
        # Atom <entry>
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            link=""
            for l in entry.findall("{http://www.w3.org/2005/Atom}link"):
                if l.get("rel","alternate")=="alternate" and l.get("href"):
                    link=l.get("href").strip(); break
            if not link:
                idt=entry.findtext("{http://www.w3.org/2005/Atom}id") or ""
                link=idt.strip()
            out.append(link)
    except Exception:
        pass
    # dedupe keep order
    seen=set(); ded=[]
    for u in out:
        if not (u and u.startswith("http")): continue
        if u in seen: continue
        seen.add(u); ded.append(u)
    return ded

def main():
    os.makedirs(ROOT, exist_ok=True)
    if not os.path.exists(FEEDS):
        print(json.dumps({"ok":False,"error":"feeds_news.txt missing"})); return
    st=_load_state()
    seen_hash=st.get("seen",{})
    already=set()
    already |= _load_lines(QUEUE)
    already |= _load_lines(SOURCES)
    block=_load_block()

    added=0; perfeed={}
    now=int(time.time())

    for feed in [ln.strip() for ln in open(FEEDS,"r",encoding="utf-8",errors="ignore") if ln.strip() and not ln.strip().startswith("#")]:
        if added >= GLOBAL_CAP: break
        meta=st["feeds"].get(feed, {})
        code, data, hdr=_fetch(feed, etag=meta.get("etag"), lm=meta.get("lm"))
        if code==304:
            continue
        if code!=200 or not data:
            continue
        st["feeds"][feed]={"etag":hdr.get("etag",""), "lm":hdr.get("lm","")}
        links=_parse_links(data)
        # APPLY BLOCKLIST HERE
        links=[u for u in links if not _blocked(u, block)]

        put=0
        for u in links:
            if added>=GLOBAL_CAP or put>=MAX_PER_FEED: break
            h=_hash(u)
            if u in already or h in seen_hash: continue
            with open(QUEUE,"a",encoding="utf-8") as q:
                q.write(f"{u}\t{feed}\t{now}\n")
            with open(SOURCES,"a",encoding="utf-8") as s:
                s.write(u+"\n")
            seen_hash[h]=now
            added+=1; put+=1; perfeed[feed]=perfeed.get(feed,0)+1

    # persist state
    st["seen"]=seen_hash
    _save_state(st)
    print(json.dumps({"ok":True,"added":added,"per_feed":perfeed}))
if __name__=="__main__":
    main()
