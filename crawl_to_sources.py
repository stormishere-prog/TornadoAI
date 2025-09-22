#!/data/data/com.termux/files/usr/bin/python3
import re, sys, os, urllib.parse, urllib.request, time
UA={"User-Agent":"Mozilla/5.0"}
ROOT="/storage/emulated/0/Download/TornadoAI"
SRC=os.path.join(ROOT,"sources.txt")

def fetch(url, timeout=20):
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","ignore"), (r.headers.get("Content-Type") or "").lower()

def abslink(base, href): return urllib.parse.urljoin(base, href)
def same_host(a,b): return urllib.parse.urlparse(a).netloc==urllib.parse.urlparse(b).netloc

def harvest(start_url, max_pages=15, max_pdfs=60, delay=1.0):
    seen={start_url}; q=[start_url]; pdfs=[]
    while q and len(seen)<=max_pages and len(pdfs)<max_pdfs:
        u=q.pop(0)
        try: html,ct=fetch(u)
        except Exception: continue
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
            href=m.group(1).strip(); link=abslink(u, href)
            if not same_host(start_url, link): continue
            if link.lower().endswith(".pdf"):
                if link not in pdfs: pdfs.append(link)
            else:
                if (len(seen)<max_pages and link not in seen and
                    re.search(r'(readingroom|foia|vault|ic-on-the-record|foia-library)', link, re.I)):
                    seen.add(link); q.append(link)
        time.sleep(delay)
    return pdfs

def append_sources(urls):
    os.makedirs(ROOT, exist_ok=True)
    old=set()
    if os.path.exists(SRC):
        for ln in open(SRC,"r",encoding="utf-8",errors="ignore"):
            ln=ln.strip()
            if ln and not ln.startswith("#"): old.add(ln)
    added=0
    with open(SRC,"a",encoding="utf-8") as f:
        for u in urls:
            if u not in old: f.write(u+"\n"); added+=1
    return added

def main():
    if len(sys.argv)<2:
        print("usage: crawl_to_sources.py <portal_url> [max_pdfs]"); sys.exit(2)
    start=sys.argv[1]; max_pdfs=int(sys.argv[2]) if len(sys.argv)>2 else 60
    pdfs=harvest(start, max_pages=15, max_pdfs=max_pdfs, delay=1.0)
    added=append_sources(pdfs)
    print({"ok":True,"found":len(pdfs),"added_to_sources":added,"portal":start})
if __name__=="__main__": main()
