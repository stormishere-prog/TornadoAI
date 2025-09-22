#!/data/data/com.termux/files/usr/bin/python3
import os, re, json, time, html, sqlite3, urllib.request, urllib.error

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
UA={"User-Agent":"Mozilla/5.0 TornadoAI/1.0 (+android; termux)"}

# Simple fetch with retries
def fetch(url, tries=2, delay=1.5):
    req=urllib.request.Request(url, headers=UA)
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8","ignore")
        except Exception:
            if i+1<tries: time.sleep(delay)
    return ""

# Extractors
META = re.compile(r'<meta\s+(?:name|property)=["\'](?:og:description|twitter:description)["\']\s+content=["\'](.*?)["\']', re.I)
LDJSON = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I|re.S)
BR = re.compile(r'<br\s*/?>', re.I)

def extract_full(html_txt):
    # Try meta descriptions first
    metas = META.findall(html_txt or "")
    for m in metas:
        txt = html.unescape(m)
        # Some metas keep <br> – normalize to newlines
        txt = BR.sub("\n", txt)
        if txt.strip():
            return txt.strip()

    # Try LD+JSON blobs for "articleBody" (or "summary")
    for blob in LDJSON.findall(html_txt or ""):
        try:
            data = json.loads(blob.strip())
            # Sometimes it's a list
            cand = []
            if isinstance(data, dict):
                cand.append(data)
            elif isinstance(data, list):
                cand.extend(data)
            for obj in cand:
                for key in ("articleBody","description","summary"):
                    if isinstance(obj, dict) and key in obj and isinstance(obj[key], str) and obj[key].strip():
                        t = html.unescape(obj[key])
                        t = BR.sub("\n", t)
                        return t.strip()
        except Exception:
            pass
    return ""

def main():
    since = int(time.time()) - 2*86400   # last 48h
    max_rows = 400                       # safety cap

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        # Pick truth posts that look short/truncated (content < 400 chars) in last 48h
        rows = c.execute("""
            SELECT url
            FROM docs
            WHERE doc_type='truth'
              AND ts_utc >= ?
              AND LENGTH(IFNULL(content,'')) < 400
            ORDER BY ts_utc DESC
            LIMIT ?
        """, (since, max_rows)).fetchall()

        updated = 0
        for (url,) in rows:
            if not url: continue
            html_txt = fetch(url, tries=2, delay=1.8)
            if not html_txt: 
                time.sleep(0.6)
                continue
            body = extract_full(html_txt)
            if not body:
                time.sleep(0.6)
                continue
            # Normalize whitespace (preserve newlines)
            body = "\n".join(line.rstrip() for line in body.splitlines()).strip()
            # Update both docs.content and doc_pages(1)
            c.execute("UPDATE docs SET content=?, page_count=1 WHERE url=?", (body, url))
            c.execute("INSERT OR REPLACE INTO doc_pages(url,page_no,content) VALUES(?,?,?)", (url, 1, body))
            updated += 1
            time.sleep(0.6)  # be polite
        c.commit()
    print(json.dumps({"ok": True, "updated": updated}))

if __name__=="__main__":
    main()
