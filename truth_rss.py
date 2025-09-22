#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, urllib.request, urllib.error, xml.etree.ElementTree as ET

ROOT="/storage/emulated/0/Download/TornadoAI"
FEED="https://truthsocial.com/@realDonaldTrump.rss"   # Atom/RSS feed; no API
STATE=os.path.join(ROOT, "truth_rss.state.json")
SOURCES=os.path.join(ROOT, "sources.txt")
UA={"User-Agent":"Mozilla/5.0 TornadoAI/1.0","Accept-Language":"en-US,en;q=0.8"}

def get(url):
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def load_state():
    try: return json.load(open(STATE,"r",encoding="utf-8"))
    except: return {"seen": []}

def save_state(st):
    tmp=STATE+".tmp"
    json.dump(st, open(tmp,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)

def parse_links(xml_bytes):
    out=[]
    try:
        root=ET.fromstring(xml_bytes)
        # RSS items
        for it in root.findall(".//item"):
            link=(it.findtext("link") or "").strip()
            if link.startswith("http"): out.append(link)
        # Atom entries
        for en in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            link=""
            for l in en.findall("{http://www.w3.org/2005/Atom}link"):
                if l.get("rel","alternate")=="alternate" and l.get("href"): link=l.get("href").strip(); break
            if not link:
                link=(en.findtext("{http://www.w3.org/2005/Atom}id") or "").strip()
            if link.startswith("http"): out.append(link)
    except Exception:
        pass
    # keep order, dedupe
    seen=set(); ded=[]
    for u in out:
        if u in seen: continue
        seen.add(u); ded.append(u)
    return ded

def main():
    os.makedirs(ROOT, exist_ok=True)
    st=load_state(); seen=set(st.get("seen",[]))
    try:
        xml=get(FEED)
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)})); sys.exit(0)
    links=parse_links(xml)
    new=[u for u in links if u not in seen]
    if new:
        # append to sources.txt
        with open(SOURCES,"a",encoding="utf-8") as f:
            for u in new:
                f.write(u+"\n")
        st["seen"]= (list(seen) + new)[-2000:]  # remember last 2000
        save_state(st)
    print(json.dumps({"ok":True,"added":len(new)}))

if __name__=="__main__":
    main()
