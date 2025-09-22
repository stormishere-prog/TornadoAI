#!/usr/bin/env python3
import json, os, re, sqlite3, sys, time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# --- constants/paths ---
HOST = "127.0.0.1"      # bind locally
PORT = 0                # 0 = dynamic choose-free-port
ROOT = os.path.abspath(os.getcwd())
DB_PATH = os.path.join(ROOT, "corpus.db")
BACKUP_DIR = os.path.join(ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- db helpers ---
def _init_schema(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
      url TEXT PRIMARY KEY, title TEXT, content TEXT, ts_utc INTEGER,
      source_trust INTEGER DEFAULT 0, sha256 TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS evidence_log(
      ts_utc INTEGER, source TEXT, snippet TEXT, tags TEXT, sha256 TEXT, score_breakdown TEXT
    );
    CREATE TABLE IF NOT EXISTS staging_docs(
      url TEXT, title TEXT, content TEXT, ts_utc INTEGER, source_trust INTEGER,
      sha256 TEXT, valid INT DEFAULT 0, notes TEXT
    );
    """)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE);")

def db_connect_rw():
    first = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute("PRAGMA temp_store=FILE;")
    conn.execute("PRAGMA foreign_keys=ON;")
    if first: _init_schema(conn)
    return conn

def db_quick_check(c):
    try:
        return c.execute("PRAGMA quick_check;").fetchone()[0]
    except Exception as e:
        return f"error:{e}"

# --- system metrics (simple) ---
def read_mem_pct():
    try:
        with open("/proc/meminfo","r") as f:
            txt=f.read()
        total=int(re.search(r"MemTotal:\s+(\d+)",txt).group(1))
        avail=int(re.search(r"MemAvailable:\s+(\d+)",txt).group(1))
        return round(100.0*(total-avail)/total,2)
    except Exception:
        return 0.0

def read_cpu_pct():
    try:
        def snap():
            with open("/proc/stat","r") as f: p=f.readline().split()
            u,n,s,i = map(int, p[1:5]); return u,n,s,i
        a=snap(); time.sleep(0.12); b=snap()
        idle=b[3]-a[3]; total=(sum(b)-sum(a))
        return 0.0 if total<=0 else round(100.0*(total-idle)/total,2)
    except Exception:
        return 0.0

# --- API core ---
def handle_api(path, body):
    # health
    if path=="/api/health":
        with db_connect_rw() as c:
            return 200, {"quick_check": db_quick_check(c),
                         "backups": sorted(os.listdir(BACKUP_DIR))}
    # current port
    if path=="/api/port":
        return 200, {"port": PORT}
    # ping
    if path=="/api/ping":
        return 200, {"ok": True, "ts": int(time.time())}
    # simple sys metrics (optional)
    if path=="/api/sys/cpu_mem":
        return 200, {"cpu": read_cpu_pct(), "mem": read_mem_pct()}
    # placeholder for your news2 ingestion (does nothing yet, but returns JSON)
    if path=="/api/fetch/news2":
        return 200, {"ok": True, "added": 0, "note": "stub endpoint"}
    if path=="/api/ask":
        # Retrieval + lite web signal + confidence & factors
        try:
            import json, sqlite3, time
            data=json.loads(body or b"{}")
            q=(data.get("question") or "").strip()
            use_web=bool(data.get("web", True))
        except Exception:
            return 400, {"error":"bad json"}
        if not q:
            return 400, {"error":"empty question"}

        # local hits (fast LIKE for phone perf)
        local=[]
        try:
            conn=sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
            cur=conn.execute(
                "SELECT url, IFNULL(title,''), substr(content,1,400) "
                "FROM docs WHERE content LIKE ? OR title LIKE ? "
                "ORDER BY length(content) LIMIT 5", (f"%{q}%", f"%{q}%"))
            local=cur.fetchall()
        except Exception:
            pass
        finally:
            try: conn.close()
            except: pass

        # web snippet (optional)
        web_text = duckduckgo_snippet(q) if use_web else ""

        # simple propaganda/evidence tagger
        def tags_for(t):
            low=(t or "").lower()
            hits=[]
            for k,tag in [("breaking","sensational"),("must see","clickbait"),
                          ("experts say","appeal_to_authority"),("anonymous sources","appeal_to_authority"),
                          ("debunked","framing"),("fact check","framing")]:
                if k in low: hits.append(tag)
            return list(set(hits)) or ["clean"]

        # confidence calc
        local_hits=len(local)
        has_primary=any(u and (u.startswith("https://www.whitehouse.gov")
                          or u.startswith("https://www.govinfo.gov")
                          or u.startswith("https://www.supremecourt.gov"))
                        for (u,_,_) in local)
        conf = min(99, max(1, 10*min(local_hits,3) + (20 if has_primary else 0) + (10 if web_text else 0)))
        label = "FACT" if conf>=90 else "GUESS"
        factors = []
        factors.append(f"sources={local_hits}")
        if has_primary: factors.append("primary_source")
        if web_text: factors.append("web_signal")

        # compose
        lines=[]
        if label=="GUESS":
            lines.append(f"GUESS — {conf}% confidence (limited corroboration).")
        else:
            lines.append(f"FACT — {conf}% confidence.")
        if local:
            for (u,t,snip) in local[:3]:
                lines.append(f"• {t or '(untitled)'} — {u}\n  {snip}")
        else:
            lines.append("• No strong local hits.")
        if web_text:
            lines.append("• Web signal:\n  " + web_text[:300])
        lines.append("If I have to guess, it’s based on the above signals. Want me to fetch more sources?")
        answer = "\n".join(lines)[:1800]

        # log web evidence (if any)
        if web_text:
            try:
                conn=sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
                conn.execute("INSERT INTO evidence_log(ts_utc,source,snippet,tags,sha256,score_breakdown) "
                             "VALUES(?,?,?,?,?,?)",
                             (int(time.time()), f"websearch:{q}", web_text[:500],
                              ",".join(tags_for(web_text)),"","ask_v1"))
                conn.close()
            except Exception:
                pass

        return 200, {"answer":answer, "confidence":conf, "label":label,
                     "factors":", ".join(factors),
                     "citations":[{"url":u,"title":t} for (u,t,_) in local]}

def safe_api(path, body):
    try:
        return handle_api(path, body)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("[api] EXCEPTION on", path, "->", e, "\n", tb)
        return 500, {"error": "internal", "detail": str(e)}

# --- HTTP handler ---
from urllib.request import Request, urlopen
def duckduckgo_snippet(q, timeout=5):
    try:
        url="https://html.duckduckgo.com/html/?q="+q.replace(" ","+")
        req=Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as r:
            raw=r.read().decode("utf-8","ignore")
        txt = re.sub(r"<[^>]+>"," ", raw)
        return scrub(txt)[:800]
    except Exception:
        return ""

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        try:
            sys.stdout.write("[req] " + (fmt % args) + "\n")
        except Exception:
            pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                code, obj = safe_api(parsed.path, None)
                return self._send_json(code, obj)
            # serve index.html by default
            if parsed.path in ("/","/index.html"):
                return super().do_GET()
            return super().do_GET()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("[do_GET] EXCEPTION", e, "\n", tb)
            try: self._send_json(500, {"error":"internal","detail":str(e)})
            except Exception: pass

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            ln = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(ln) if ln > 0 else b""
            if parsed.path.startswith("/api/"):
                code, obj = safe_api(parsed.path, body)
                return self._send_json(code, obj)
            self._send_json(404, {"error":"not found"})
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("[do_POST] EXCEPTION", e, "\n", tb)
            try: self._send_json(500, {"error":"internal","detail":str(e)})
            except Exception: pass

# --- main ---
def main():
    global PORT
    os.chdir(ROOT)
    with db_connect_rw() as c:
        print(f"[db] quick_check={db_quick_check(c)}")

    HTTPServer.allow_reuse_address = True
    print(f"[dev] trying bind {HOST}:{PORT or '(dynamic)'}")
    httpd = HTTPServer((HOST, PORT), Handler)

    # record the chosen port, update global, and write port.txt
    PORT = httpd.server_address[1]
    open(os.path.join(ROOT, "port.txt"), "w").write(str(PORT))
    print(f"[dev] Serving {ROOT} on http://{HOST}:{PORT}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()


# ---- helpers for news ingest (RSS/Atom + HTML fallback) ----
from urllib.request import Request, urlopen

def scrub(t):
    import re
    return re.sub(r"\s{2,}"," ", re.sub(r"[!]{2,}","!", t or "")).strip()

def http_get(url, timeout=6):
    try:
        req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get("Content-Type","text/plain") or "").lower()
            text  = r.read().decode("utf-8","ignore")
        return text, ctype
    except Exception:
        return "", ""

def parse_rss(xml_text):
    # Very small extractor: items -> (title, link, summary)
    import re
    items = []
    t = xml_text or ""
    blocks = re.findall(r"<item[\\s\\S]*?</item>", t, re.I) or re.findall(r"<entry[\\s\\S]*?</entry>", t, re.I)
    for b in blocks[:30]:
        def pick(pats):
            for pat in pats:
                m = re.search(pat, b, re.I)
                if m: return m.group(1).strip()
            return ""
        title = pick([r"<title[^>]*>([\\s\\S]*?)</title>"])
        link  = pick([r"<link[^>]*href=\\\"([^\\\"]+)\\\"[^>]*/?>", r"<link[^>]*>([\\s\\S]*?)</link>"])
        desc  = pick([r"<description[^>]*>([\\s\\S]*?)</description>", r"<summary[^>]*>([\\s\\S]*?)</summary>"])
        # strip tags
        strip = lambda x: scrub(re.sub(r"<[^>]+>"," ", x or ""))
        title, link, desc = strip(title), strip(link), strip(desc)
        if title or desc:
            items.append((title, link, desc))
    return items

def fetch_text(url, timeout=6):
    # HTML-first paragraph / meta description fallback
    try:
        req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8","ignore")
        import re
        html = re.sub(r"<script[\\s\\S]*?</script>"," ", html, flags=re.I)
        html = re.sub(r"<style[\\s\\S]*?</style>"," ", html, flags=re.I)
        tit  = re.search(r"<title[^>]*>([\\s\\S]*?)</title>", html, re.I)
        meta = re.search(r"<meta[^>]+name=\\\"description\\\"[^>]+content=\\\"([^\\\"]+)\\\"", html, re.I)
        para = re.search(r"<p[^>]*>([\\s\\S]*?)</p>", html, re.I)
        def strip(x): return scrub(re.sub(r"<[^>]+>"," ", x or ""))
        title = strip(tit.group(1) if tit else "")
        desc  = strip(meta.group(1) if meta else "")
        p1    = strip(para.group(1) if para else "")
        text  = (title+" — "+(desc or p1)) if title else (desc or p1)
        return text[:1200]
    except Exception:
        return ""

def fetch_news_ingest(root, db_connect_rw):
    import time, sqlite3, os
    p = os.path.join(root, "news_sources.txt")
    if not os.path.exists(p):
        return 400, {"error":"news_sources.txt not found in project root"}
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        sources = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

    total = 0
    with db_connect_rw() as c:
        c.execute("BEGIN IMMEDIATE;")
        try:
            for src in sources[:16]:   # cap per call
                text, ctype = http_get(src)
                is_xml = ("xml" in ctype) or src.endswith(".xml") or src.endswith("/feed/")
                if is_xml and text:
                    items = parse_rss(text)
                    for (title, link, summary) in items[:40]:
                        body = (summary or title or "")[:800]
                        tgs  = "clean" if body else "empty"
                        c.execute("INSERT INTO evidence_log(ts_utc,source,snippet,tags,sha256,score_breakdown) VALUES(?,?,?,?,?,?)",
                                  (int(time.time()), link or src, f"{title} — {body}"[:800], tgs, "", "news_rss"))
                        key = link or (src + "#" + (title[:60] if title else "item"))
                        c.execute("INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_trust,sha256) VALUES(?,?,?,?,?,?)",
                                  (key, title or "(untitled)", body, int(time.time()), 50, ""))
                        total += 1
                else:
                    snippet = fetch_text(src)[:800]
                    tgs = "clean" if snippet else "empty"
                    c.execute("INSERT INTO evidence_log(ts_utc,source,snippet,tags,sha256,score_breakdown) VALUES(?,?,?,?,?,?)",
                              (int(time.time()), src, snippet, tgs, "", "news_html"))
                    c.execute("INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_trust,sha256) VALUES(?,?,?,?,?,?)",
                              (src, "(page)", snippet, int(time.time()), 40, ""))
                    total += 1
            c.execute("COMMIT;")
        except Exception as e:
            c.execute("ROLLBACK;")
            return 500, {"error": f"news_failed:{e}"}
    return 200, {"ok": True, "added": total}
# ---- end helpers ----
