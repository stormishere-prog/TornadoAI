#!/data/data/com.termux/files/usr/bin/python3
import os, re, time, json, sqlite3, html, urllib.request, urllib.parse

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")
SRC  = os.path.join(ROOT, "sources.txt")
UA   = {"User-Agent":"Mozilla/5.0"}
NOW  = int(time.time())

VIDEO_EXTS = (".mp4",".webm",".mkv",".m4v",".mov",".m3u8",".mpd",".ism",".ts")
VIDEO_HINTS = ("video/", "application/vnd.apple.mpegurl", "application/x-mpegURL", "application/dash+xml")

def fetch(u, timeout=25):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get("Content-Type","").lower()
        body = r.read().decode("utf-8","ignore")
        return body, ctype

def absu(base, href): return urllib.parse.urljoin(base, href)

def guess_mime(url, ctype_hdr=""):
    u = url.lower()
    if ctype_hdr:
        for h in VIDEO_HINTS:
            if h in ctype_hdr: return ctype_hdr
    if u.endswith(".mp4"):  return "video/mp4"
    if u.endswith(".webm"): return "video/webm"
    if u.endswith(".mkv"):  return "video/x-matroska"
    if u.endswith(".m4v"):  return "video/mp4"
    if u.endswith(".mov"):  return "video/quicktime"
    if u.endswith(".m3u8"): return "application/vnd.apple.mpegurl"
    if u.endswith(".mpd"):  return "application/dash+xml"
    if u.endswith(".ism"):  return "application/vnd.ms-sstr+xml"
    if u.endswith(".ts"):   return "video/mp2t"
    return ctype_hdr or "video/unknown"

def looks_video_url(u):
    lu = u.lower()
    if lu.startswith("data:"): return False
    if any(lu.endswith(ext) for ext in VIDEO_EXTS): return True
    # Hints in query or path
    if "m3u8" in lu or "dash" in lu or "manifest" in lu: return True
    return False

def upsert_doc_media(c, media_url, title="", note=""):
    # minimal doc row so it’s trackable alongside everything else
    c.execute("""
      INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_trust,sha256,kind,page_count)
      VALUES(?,?,?,?,?,?,?,?)
    """, (media_url, title or os.path.basename(urllib.parse.urlparse(media_url).path) or "media",
          note or "", NOW, 60, "", "media", 0))

def add_media_ref(c, page_url, media_url, mime):
    c.execute("""
      INSERT OR IGNORE INTO media_refs(page_url, media_url, mime, ts_utc)
      VALUES(?,?,?,?)
    """, (page_url, media_url, mime, NOW))

def harvest_from_page(c, page_url):
    try:
        htmltxt, ctype = fetch(page_url)
    except Exception:
        return 0
    found = set()

    # <video src="..."> and <source src="...">
    for m in re.finditer(r'(?is)<(?:video|source)\b[^>]*?\bsrc=["\']([^"\']+)["\']', htmltxt):
        link = absu(page_url, m.group(1))
        if looks_video_url(link):
            found.add(link)

    # <a href="..."> that look like video assets
    for m in re.finditer(r'(?is)<a\b[^>]*?href=["\']([^"\']+)["\']', htmltxt):
        link = absu(page_url, m.group(1))
        if looks_video_url(link):
            found.add(link)

    # record
    added = 0
    for v in found:
        mime = guess_mime(v)
        add_media_ref(c, page_url, v, mime)
        upsert_doc_media(c, v, title=os.path.basename(urllib.parse.urlparse(v).path), note=f"Found on {page_url}")
        added += 1
    return added

def main():
    if not os.path.exists(SRC):
        print(json.dumps({"ok":False,"error":"sources.txt missing"})); return
    pages = [ln.strip() for ln in open(SRC,"r",encoding="utf-8",errors="ignore")
             if ln.strip() and not ln.strip().startswith("#")]
    total=0
    with sqlite3.connect(DB) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        c.execute("BEGIN IMMEDIATE;")
        try:
            for u in pages:
                # only scan HTML-ish pages (quick filter)
                if u.lower().endswith(".pdf"): 
                    continue
                if any(u.lower().endswith(ext) for ext in VIDEO_EXTS):
                    # direct video already in sources.txt – record it as media
                    add_media_ref(c, page_url=u, media_url=u, mime=guess_mime(u))
                    upsert_doc_media(c, u, title=os.path.basename(urllib.parse.urlparse(u).path))
                    total += 1
                else:
                    total += harvest_from_page(c, u)
            c.execute("COMMIT;")
        except Exception as e:
            c.execute("ROLLBACK;")
            print(json.dumps({"ok":False,"error":str(e)})); return
    print(json.dumps({"ok":True,"media_added":total}, ensure_ascii=False))

if __name__=="__main__": main()
