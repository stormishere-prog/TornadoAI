#!/data/data/com.termux/files/usr/bin/python3
import os, re, json, time, sqlite3, itertools, urllib.parse
ROOT="/storage/emulated/0/Download/TornadoAI"; DB=os.path.join(ROOT,"corpus.db")
NEG = re.compile(r'\b(no|not|den(y|ies|ied)|false|contradict|dispute|refute|hoax|fake)\b', re.I)
NAME = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b')

def _host(u):
    try: return urllib.parse.urlparse(u).netloc.lower()
    except: return ""

def _to_text(x):
    if x is None: return ""
    if isinstance(x, bytes):
        try: return x.decode("utf-8","ignore")
        except: return str(x)
    return str(x)

def main():
    with sqlite3.connect(DB, timeout=30) as c:
        rows=c.execute("""
          SELECT d.url, IFNULL(d.title,''), IFNULL(s.summary,'')
          FROM docs d LEFT JOIN doc_summaries s ON d.url=s.url
          WHERE d.ts_utc >= strftime('%s','now')-14*86400
        """).fetchall()
        buckets={}
        for url, title, summ in rows:
            title=_to_text(title); summ=_to_text(summ); url=_to_text(url)
            text=(title+" "+summ)
            names=set(m.group(1) for m in NAME.finditer(text) if len(m.group(1))>2)
            if not names: names={_host(url)}
            key="|".join(sorted(names))[:120]
            buckets.setdefault(key, []).append((url,title,summ))
        now=int(time.time())
        for key, docs in buckets.items():
            for (aurl, at, asu), (burl, bt, bsu) in itertools.combinations(docs,2):
                ta=(at+" "+asu); tb=(bt+" "+bsu)
                if NEG.search(ta) and not NEG.search(tb):
                    c.execute("INSERT OR IGNORE INTO contradictions(a_url,b_url,reason,ts_utc) VALUES(?,?,?,?)",
                              (aurl,burl,f"negation vs non-negation for topic {key}",now))
                elif NEG.search(tb) and not NEG.search(ta):
                    c.execute("INSERT OR IGNORE INTO contradictions(a_url,b_url,reason,ts_utc) VALUES(?,?,?,?)",
                              (burl,aurl,f"negation vs non-negation for topic {key}",now))
        c.commit()
    print(json.dumps({"ok":True}))
if __name__=="__main__": main()
