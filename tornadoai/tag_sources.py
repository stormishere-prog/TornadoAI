#!/data/data/com.termux/files/usr/bin/python3
import os, re, json, sqlite3, urllib.parse
ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

RULES=[]
def _load_rules():
    path=os.path.join(ROOT,"source_tags.txt")
    if not os.path.exists(path): return
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        for ln in f:
            ln=ln.strip()
            if not ln or ln.startswith("#"): continue
            parts=re.split(r'\s+', ln, maxsplit=1)
            if len(parts)!=2: continue
            tag, pat = parts[0].lower(), parts[1].lower()
            RULES.append((tag, pat))

def _host(u:str)->str:
    try: return urllib.parse.urlparse(u).netloc.lower()
    except: return ""

def tag_for(u:str)->str:
    if not u: return "unknown"
    h=_host(u); lu=u.lower()
    for tag,pat in RULES:
        if pat in h or pat in lu:
            return tag
    return "unknown"

def main():
    _load_rules()
    n=0
    with sqlite3.connect(DB, timeout=30) as c:
        # ✅ retag ALL docs (no WHERE)
        for (u,) in c.execute("SELECT url FROM docs").fetchall():
            c.execute("UPDATE docs SET source_tag=? WHERE url=?",(tag_for(u),u)); n+=1
        c.commit()
    print(json.dumps({"ok":True,"tagged":n}))

if __name__=="__main__":
    main()
