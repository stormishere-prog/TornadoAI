#!/data/data/com.termux/files/usr/bin/python3
import os, re, json, sqlite3, urllib.parse, time

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

TRACK_PARAMS=set("""
utm_source utm_medium utm_campaign utm_term utm_content
utm_id utm_name utm_reader utm_social utm_viz_id utm_brand
mc_cid mc_eid ref ref_src gclid dclid fbclid
igshid si cid src s kw rd amp jsmodule mkt_tok
""".split())

def canon(url:str)->str:
    try:
        p=urllib.parse.urlparse(url)
        qs=urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        qs2=[(k,v) for k,v in qs if k.lower() not in TRACK_PARAMS]
        qstr=urllib.parse.urlencode(qs2, doseq=True)
        path=p.path.rstrip('/') if p.path not in ('/','') else p.path
        # strip AMP variants
        path=re.sub(r'/amp/?$','',path,flags=re.I)
        # normalize www
        netloc=p.netloc.lower().replace('www.','',1)
        return urllib.parse.urlunparse((p.scheme.lower(), netloc, path, '', qstr, ''))
    except Exception:
        return url

def main():
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        c.execute("""CREATE TABLE IF NOT EXISTS url_canon(
            url TEXT PRIMARY KEY,
            canon TEXT
        );""")
        c.execute("""CREATE VIEW IF NOT EXISTS v_docs_by_canon AS
            SELECT uc.canon, d.url, d.title, d.ts_utc
            FROM docs d
            JOIN url_canon uc ON uc.url=d.url
            ORDER BY uc.canon, d.ts_utc DESC;""")
        # populate new rows
        urls=[r[0] for r in c.execute("SELECT url FROM docs WHERE url LIKE 'http%'")]
        n_ins=0
        for u in urls:
            if c.execute("SELECT 1 FROM url_canon WHERE url=?",(u,)).fetchone(): continue
            c.execute("INSERT INTO url_canon(url,canon) VALUES(?,?)",(u, canon(u)))
            n_ins+=1
        c.commit()
        # quick dupes report path
        report=os.path.join(ROOT,"reports")
        os.makedirs(report, exist_ok=True)
        out=os.path.join(report,"news_dupes.tsv")
        cur=c.execute("""SELECT canon, COUNT(*) n
                         FROM url_canon WHERE canon LIKE 'http%'
                         GROUP BY canon HAVING n>1 ORDER BY n DESC, canon""")
        rows=cur.fetchall()
        with open(out,"w",encoding="utf-8") as f:
            f.write("canon\tcount\n")
            for r in rows:
                f.write(f"{r[0]}\t{r[1]}\n")
        print(json.dumps({"ok":True,"inserted":n_ins,"dupe_groups":len(rows),"tsv":out}))
if __name__=="__main__": main()
