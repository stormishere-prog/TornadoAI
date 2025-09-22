#!/data/data/com.termux/files/usr/bin/python3
import os, time, sqlite3, urllib.request, urllib.error

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
UA={"User-Agent":"Mozilla/5.0"}

def probe(url:str)->tuple[int,str]:
    # Try Range probe first (cheap), then fallback to small GET
    try:
        req=urllib.request.Request(url, headers={**UA,"Range":"bytes=0-0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return (getattr(r, "status", 200), "")
    except Exception as e1:
        try:
            req=urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return (getattr(r,"status",200), "")
        except Exception as e2:
            msg=str(e2)
            code=getattr(getattr(e2,'fp',None),'status', None) or getattr(e2,'code', None) or 0
            return (int(code), msg[:300])

def main():
    now=int(time.time())
    urls=set()
    # crawl from docs + sources.txt (so we also check un-ingested)
    try:
        with open(os.path.join(ROOT,"sources.txt"),"r",encoding="utf-8",errors="ignore") as f:
            for ln in f:
                ln=ln.strip()
                if ln and not ln.startswith("#"):
                    urls.add(ln)
    except FileNotFoundError:
        pass

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        for (u,) in c.execute("SELECT url FROM docs"):
            urls.add(u)

        ok=err=0
        for u in sorted(urls):
            code, note = probe(u)
            if 200 <= code < 400:
                c.execute("""INSERT INTO fetch_log(url,last_ok_utc,last_status,err_note,count_ok)
                             VALUES(?,?,?,?,1)
                             ON CONFLICT(url) DO UPDATE SET
                               last_ok_utc=?,
                               last_status=?,
                               err_note='',
                               count_ok=COALESCE(fetch_log.count_ok,0)+1
                           """, (u, now, code, '', now, code))
                ok+=1
            else:
                c.execute("""INSERT INTO fetch_log(url,last_err_utc,last_status,err_note,count_err)
                             VALUES(?,?,?,?,1)
                             ON CONFLICT(url) DO UPDATE SET
                               last_err_utc=?,
                               last_status=?,
                               err_note=?,
                               count_err=COALESCE(fetch_log.count_err,0)+1
                           """, (u, now, code, note, now, code, note))
                err+=1
        print({"ok":True,"checked":len(urls),"ok_count":ok,"err_count":err})

if __name__=="__main__":
    main()
