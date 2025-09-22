#!/data/data/com.termux/files/usr/bin/python3
import os, re, time, sqlite3, hashlib, html, urllib.request, subprocess, tempfile, sys

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
UA={"User-Agent":"Mozilla/5.0"}

def sha256(b): import hashlib; return hashlib.sha256(b).hexdigest()
def is_pdf_bytes(b:bytes)->bool: return b[:4].lower()==b"%pdf"

def fetch(url:str)->bytes:
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r: return r.read()

def text_from_html(b:bytes)->str:
    t=b.decode("utf-8","ignore")
    t=re.sub(r"(?is)<script[^>]*>.*?</script>"," ",t)
    t=re.sub(r"(?is)<style[^>]*>.*?</style>"," ",t)
    t=re.sub(r"(?is)<[^>]+>"," ",t)
    t=html.unescape(t)
    t=re.sub(r"\s+"," ",t).strip()
    return t

def pdf_pages_to_text(pdf_path:str)->list[str]:
    out=[]
    try:
        pinfo=subprocess.check_output(["pdfinfo", pdf_path], timeout=30).decode("utf-8","ignore")
        import re
        m=re.search(r"Pages:\s+(\d+)", pinfo)
        pages=int(m.group(1)) if m else 0
        for p in range(1, pages+1):
            tf=tempfile.NamedTemporaryFile(delete=False, suffix=".txt"); tfp=tf.name; tf.close()
            try:
                subprocess.run(["pdftotext","-enc","UTF-8","-f",str(p),"-l",str(p),pdf_path,tfp],
                               check=True, timeout=35,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                txt=open(tfp,"r",encoding="utf-8",errors="ignore").read()
                txt=re.sub(r"\s+"," ",txt).strip()
                out.append(txt)
            finally:
                try: os.remove(tfp)
                except: pass
    except Exception:
        try:
            full=subprocess.check_output(["pdftotext","-enc","UTF-8", pdf_path, "-"], timeout=50).decode("utf-8","ignore")
            full=re.sub(r"\s+"," ",full).strip()
            out=[full] if full else []
        except Exception:
            out=[]
    return out

def short_summary(pages:list[str], limit_chars=700)->str:
    joined=" ".join(p for p in pages if p).strip()
    if not joined: return ""
    parts=re.split(r"(?<=[\.\!\?])\s+", joined)
    s=[]; tot=0
    for sent in parts:
        if not sent: continue
        s.append(sent); tot+=len(sent)
        if tot>limit_chars: break
    return " ".join(s)[:limit_chars]

def upsert_doc(c, url, title, content, kind, page_count):
    ts=int(time.time())
    sha=sha256((title or "").encode()+ (content or "").encode())
    c.execute("""INSERT OR REPLACE INTO docs(url,title,content,ts_utc,source_trust,sha256,kind,page_count)
                 VALUES(?,?,?,?,?,?,?,?)""",
              (url, title or "", content or "", ts, 70, sha, kind, page_count))

def clear_pages(c, url): c.execute("DELETE FROM doc_pages WHERE url=?",(url,))
def insert_page(c, url, page_no, text): c.execute("INSERT INTO doc_pages(url,page_no,text) VALUES(?,?,?)",(url,page_no,text or ""))
def upsert_summary(c, url, summary): c.execute("INSERT OR REPLACE INTO doc_summaries(url,summary,ts_utc) VALUES(?,?,?)",(url, summary or "", int(time.time())))

def handle_url(c, url:str)->int:
    try:
        b=fetch(url)
    except Exception as e:
        return 0
    added=0
    if is_pdf_bytes(b):
        h=sha256(b)[:16]
        cache=os.path.join(ROOT,"cache"); os.makedirs(cache, exist_ok=True)
        pdf_path=os.path.join(cache, f"{h}.pdf")
        open(pdf_path,"wb").write(b)
        pages=pdf_pages_to_text(pdf_path)
        title=os.path.basename(pdf_path)
        upsert_doc(c, url, title, pages[0] if pages else "", "pdf", len(pages))
        clear_pages(c, url)
        for i,txt in enumerate(pages, start=1): insert_page(c, url, i, txt)
        upsert_summary(c, url, short_summary(pages)); added=1
    else:
        t=text_from_html(b)
        ttl=url
        upsert_doc(c, url, ttl, t, "html", 1)
        clear_pages(c, url); insert_page(c, url, 1, t)
        upsert_summary(c, url, short_summary([t])); added=1
    return added

def main():
    urls=[ln.strip() for ln in sys.stdin if ln.strip() and not ln.strip().startswith("#")]
    if not urls: 
        print({"ok":True,"added":0,"note":"no input urls"}); return
    total=0
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        c.execute("BEGIN IMMEDIATE;")
        try:
            for u in urls: total+=handle_url(c,u)
            c.execute("COMMIT;")
        except Exception as e:
            c.execute("ROLLBACK;")
            print({"ok":False,"error":str(e)}); return
    print({"ok":True,"added":total,"urls":len(urls)})

if __name__=="__main__":
    main()
