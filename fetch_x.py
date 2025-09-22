#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, urllib.request, urllib.error, xml.etree.ElementTree as ET

ROOT   = "/storage/emulated/0/Download/TornadoAI"
WL     = os.path.join(ROOT, "watchlist_x.txt")
QUEUE  = os.path.join(ROOT, "sources.txt")  # you already ingest from here
STATE  = os.path.join(ROOT, "x_state.json") # remembers last seen per handle

NITTER = os.environ.get("NITTER_HOST","https://nitter.net")  # you can swap mirrors
MAX_PER_HANDLE = int(os.environ.get("MAX_X_PER_HANDLE","5"))
GLOBAL_CAP = int(os.environ.get("MAX_X_GLOBAL","40"))
UA = {"User-Agent":"Mozilla/5.0 TornadoAI/1.0"}

def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def _load_state():
    try:
        with open(STATE,"r",encoding="utf-8") as f:
            return json.load(f)
    except: return {"last_id":{}}

def _save_state(st):
    tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(st,f,ensure_ascii=False,indent=2)
    os.replace(tmp,STATE)

def _tweet_url_from_rss(item):
    # Try to build canonical x.com/status URL from entry link/guid
    link = (item.findtext("link") or "").strip()
    guid = (item.findtext("guid") or "").strip()
    base = link or guid
    # Common patterns on Nitter: https://nitter.net/<user>/status/<id>
    if "/status/" in base:
        try:
            user = base.split("/status/")[0].rstrip("/").split("/")[-1]
            tid  = base.split("/status/")[1].split("?")[0].split("#")[0]
            if user and tid:
                return f"https://x.com/{user}/status/{tid}"
        except: pass
    return base or guid

def main():
    if not os.path.exists(WL):
        print(json.dumps({"ok":False,"error":"watchlist_x.txt missing"})); return
    handles=[ln.strip().lstrip("@") for ln in open(WL,"r",encoding="utf-8",errors="ignore")
             if ln.strip() and not ln.strip().startswith("#")]
    st=_load_state(); last=st.get("last_id",{})
    added=0; per={}

    # For dedupe against what’s already queued/sourced, load current sources.txt
    existing=set()
    if os.path.exists(QUEUE):
        for ln in open(QUEUE,"r",encoding="utf-8",errors="ignore"):
            ln=ln.strip()
            if ln and not ln.startswith("#"): existing.add(ln)

    out_lines=[]
    for h in handles:
        rss=f"{NITTER.rstrip('/')}/{h}/rss"
        try:
            data=_get(rss)
            root=ET.fromstring(data)
        except Exception:
            continue
        seen=0
        newest=None
        for item in root.findall(".//item"):
            url=_tweet_url_from_rss(item)
            if not url or not url.startswith("http"): continue
            tid = url.split("/status/")[-1] if "/status/" in url else url
            if last.get(h) and tid <= last[h]:  # stop once we hit an old one
                continue
            if url in existing:                 # already queued
                continue
            out_lines.append(url)
            existing.add(url)
            seen+=1
            newest = max(newest or tid, tid)
            if seen >= MAX_PER_HANDLE or added+len(out_lines) >= GLOBAL_CAP:
                break
        added += seen
        per[h]=seen
        if newest: last[h]=newest
        if added >= GLOBAL_CAP: break

    if out_lines:
        with open(QUEUE,"a",encoding="utf-8") as f:
            for u in out_lines:
                f.write(u+"\n")
    st["last_id"]=last; _save_state(st)
    print(json.dumps({"ok":True,"added":added,"per":per}))
if __name__=="__main__": main()
