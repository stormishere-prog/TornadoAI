#!/data/data/com.termux/files/usr/bin/python3
import os, re, time, json, sqlite3, urllib.request, urllib.error, xml.etree.ElementTree as ET, random, html

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")
HANDLES = os.path.join(ROOT, "x_handles.txt")
NITTERS = os.path.join(ROOT, "nitter_instances.txt")
UA = {"User-Agent":"Mozilla/5.0 TornadoAI/1.0"}

X_MAX_PAGES = int(os.environ.get("X_MAX_PAGES","1"))
X_MAX_PER_HANDLE = int(os.environ.get("X_MAX_PER_HANDLE","5"))
DELAY = float(os.environ.get("X_REQUEST_DELAY","2.5"))

def _lines(path):
    if not os.path.exists(path): return []
    return [l.strip() for l in open(path,encoding="utf-8",errors="ignore") if l.strip() and not l.strip().startswith("#")]

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","ignore")

def fetch_profile_any(handle):
    bases = _lines(NITTERS)
    random.shuffle(bases)
    last_err = "no_mirrors"
    # try HTML
    for base in bases:
        try:
            html = _get(f"{base}/{handle}")
            if "timeline-item" in html or "tweet-date" in html or "<article" in html:
                return ("html", html, base)
        except Exception as e:
            last_err = f"{type(e).__name__}"
        time.sleep(DELAY)
    # try RSS
    for base in bases:
        try:
            rss = _get(f"{base}/{handle}/rss")
            if "<rss" in rss or "<feed" in rss:
                return ("rss", rss, base)
        except Exception as e:
            last_err = f"{type(e).__name__}"
        time.sleep(DELAY)
    # readable proxy fallback
    try:
        md = _get(f"https://r.jina.ai/http://x.com/{handle}")
        if md and len(md) > 500:
            return ("md", md, "r.jina.ai")
    except Exception as e:
        last_err = f"{type(e).__name__}"
    return (None, last_err, None)

def parse_rss(rss_text):
    out=[]
    try:
        root=ET.fromstring(rss_text)
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link  = (it.findtext("link") or "").strip()
            date  = (it.findtext("pubDate") or "").strip()
            desc  = (it.findtext("description") or "").strip()
            # RSS title often has full text; description may be HTML
            body = html.unescape(re.sub("<[^>]+>","",desc)) or title
            out.append((link, body, date))
    except Exception:
        pass
    return out

def parse_md(md_text):
    # crude: split on status links and grab previous non-empty lines as body
    out=[]
    lines = md_text.splitlines()
    for i,ln in enumerate(lines):
        m = re.search(r"https?://(x|twitter)\.com/[^/]+/status/\d+", ln)
        if m:
            url = m.group(0)
            # walk up to find body lines
            j=i-1; bucket=[]
            while j>=0 and lines[j].strip():
                bucket.append(lines[j].strip()); j-=1
            body = "\n".join(reversed(bucket)).strip()
            if body:
                out.append((url, body, ""))
    return out

def parse_html(html_text):
    # minimal: try to capture tweet text blocks
    out=[]
    # Nitter often wraps text in <div class="tweet-content media-body"> ... </div>
    for m in re.finditer(r'<div[^>]*class="tweet-content[^"]*"[^>]*>(.*?)</div>', html_text, re.S|re.I):
        chunk = m.group(1)
        txt = html.unescape(re.sub("<[^>]+>","",chunk)).strip()
        # try to get a status link near it
        tail = html_text[m.end(): m.end()+600]
        lm = re.search(r'href="(https?://[^"]+/status/\d+)"', tail)
        link = lm.group(1) if lm else ""
        if txt and link:
            out.append((link, txt, ""))
    return out

def upsert(c, url, body, when_ts=None):
    if not url or not body: return 0
    ts = int(time.time()) if when_ts is None else when_ts
    title = (body.strip().splitlines()[0])[:200]
    # best-effort source tag for X
    tag = "independent"
    c.execute("""
      INSERT OR REPLACE INTO docs(url,title,content,ts_utc,doc_type,source_tag,page_count)
      VALUES(?,?,?,?,?,?,?)
    """,(url, title, body, ts, "x", tag, 1))
    return 1

def main():
    handles = _lines(HANDLES)
    if not handles:
        print(json.dumps({"ok":False,"error":"x_handles.txt missing or empty"})); return
    inserted=0
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        for h in handles:
            kind, blob, src = fetch_profile_any(h)
            items=[]
            if kind=="rss":
                items = parse_rss(blob)
            elif kind=="html":
                items = parse_html(blob)
            elif kind=="md":
                items = parse_md(blob)
            else:
                continue
            # limit per handle
            for (link, body, _date) in items[:X_MAX_PER_HANDLE]:
                try:
                    inserted += upsert(c, link, body)
                except Exception:
                    pass
            time.sleep(DELAY)
        c.commit()
    print(json.dumps({"ok":True,"inserted":inserted}))
if __name__=="__main__": main()
