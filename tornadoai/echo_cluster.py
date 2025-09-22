#!/data/data/com.termux/files/usr/bin/python3
import os, re, json, time, sqlite3, urllib.parse
ROOT="/storage/emulated/0/Download/TornadoAI"; DB=os.path.join(ROOT,"corpus.db")

def _canon(u):
    if not u: return ""
    if isinstance(u, bytes):
        try: u=u.decode("utf-8","ignore")
        except: u=str(u)
    try:
        p=urllib.parse.urlparse(u)
        net=p.netloc.lower()
        path=(p.path or "/").lower()
        path=re.sub(r'/+$','',path)
        qs=urllib.parse.parse_qsl(p.query, keep_blank_values=False)
        qs=[(k,v) for (k,v) in qs if not k.lower().startswith("utm_")]
        qstr=urllib.parse.urlencode(sorted(qs))
        base=f"{net}{path}"
        return base + (("?"+qstr) if qstr else "")
    except:
        return (u or "").lower()

def _host(u):
    try: return urllib.parse.urlparse(u).netloc.lower()
    except: return ""

def main():
    now=int(time.time())
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("BEGIN IMMEDIATE;")
        rows=c.execute("SELECT d.url FROM docs d WHERE d.url IS NOT NULL AND d.url!=''").fetchall()
        seen=set()
        for (url,) in rows:
            can=_canon(url)
            c.execute("UPDATE docs SET canon=? WHERE url=?",(can,url))
            if can and can not in seen:
                c.execute("INSERT OR IGNORE INTO echo_clusters(canon,root_url,size,last_utc) VALUES(?,?,?,?)",
                          (can,url,0,now))
                seen.add(can)
            c.execute("INSERT OR IGNORE INTO echo_edges(canon,url,host,ts_utc) VALUES(?,?,?,?)",
                      (can,url,_host(url),now))
        c.execute("""
          UPDATE echo_clusters
             SET size=(SELECT COUNT(*) FROM echo_edges e WHERE e.canon=echo_clusters.canon),
                 last_utc=?
        """,(now,))
        c.commit()
    print(json.dumps({"ok":True}))
if __name__=="__main__": main()
