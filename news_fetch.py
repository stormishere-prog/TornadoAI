#!/data/data/com.termux/files/usr/bin/python3
import os, time, json, sqlite3, urllib.request, urllib.parse, xml.etree.ElementTree as ET

ROOT = "/storage/emulated/0/Download/TornadoAI"
FEEDS = os.path.join(ROOT, "news_feeds.txt")
SOURCES = os.path.join(ROOT, "sources.txt")
DB = os.path.join(ROOT, "corpus.db")
UA = {"User-Agent": "Mozilla/5.0 (TornadoAI-News/1.0)"}

PER_FEED = int(os.environ.get("NEWS_PER_FEED", "50"))      # grab up to 50 per feed
MAX_TOTAL = int(os.environ.get("NEWS_MAX_TOTAL", "500"))   # cap total per run

def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _links_from_rss(xml_bytes, base):
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return out
    # RSS 2.0: channel/item/link
    for item in root.findall(".//item"):
        link = item.findtext("link") or ""
        if link:
            out.append(urllib.parse.urljoin(base, link.strip()))
    # Atom: entry/link@href
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        for l in entry.findall("{http://www.w3.org/2005/Atom}link"):
            href = l.get("href")
            if href:
                out.append(urllib.parse.urljoin(base, href.strip()))
    return out

def _append_sources(urls):
    seen = set()
    if os.path.exists(SOURCES):
        with open(SOURCES,"r",encoding="utf-8",errors="ignore") as f:
            for ln in f:
                ln=ln.strip()
                if ln and not ln.startswith("#"): seen.add(ln)
    added = 0
    with open(SOURCES, "a", encoding="utf-8") as f:
        for u in urls:
            if u not in seen:
                f.write(u+"\n"); added += 1
                seen.add(u)
    return added

def main():
    if not os.path.exists(FEEDS):
        print(json.dumps({"ok":False,"error":"news_feeds.txt missing"})); return
    feeds = [ln.strip() for ln in open(FEEDS, "r", encoding="utf-8", errors="ignore")
             if ln.strip() and not ln.strip().startswith("#")]
    batch = []
    for feed in feeds:
        try:
            b = _get(feed)
            links = _links_from_rss(b, feed)
            # keep the newest first; feeds already ordered => slice head
            links = links[:PER_FEED]
            batch.extend(links)
        except Exception:
            continue
        if len(batch) >= MAX_TOTAL:
            break
    # de-dupe, cap total
    batch = list(dict.fromkeys(batch))[:MAX_TOTAL]
    added = _append_sources(batch)
    # run ingest (re-uses your existing pipeline)
    os.chdir(ROOT)
    os.system("python3 fetch_and_ingest.py > /dev/null 2>&1 || true")
    print(json.dumps({"ok":True,"feeds":len(feeds),"candidates":len(batch),"added_to_sources":added}))
if __name__=="__main__": main()
