#!/data/data/com.termux/files/usr/bin/python3
import re, os, time, urllib.parse, urllib.request, html
ROOT="/storage/emulated/0/Download/TornadoAI"
SRC=os.path.join(ROOT,"sources.txt")
UA={"User-Agent":"Mozilla/5.0"}
NOW=time.time()

def fetch(u, timeout=25):
    req=urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","ignore")

def absu(base, href): return urllib.parse.urljoin(base, href)

# crude recent check: allow URLs/text mentioning 2024/2025 or dates within ~120 days
Y_PAT=re.compile(r'\b(2024|2025)\b')
DATE_PATS=[
    (re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+(20\d{2})',re.I),'%b %d, %Y'),
    (re.compile(r'\b\d{1,2}/\d{1,2}/(20\d{2})\b'),'%m/%d/%Y'),
    (re.compile(r'\b(20\d{2})-(\d{2})-(\d{2})\b'),'iso')
]
def is_recent(blob:str, max_age_days=120):
    if Y_PAT.search(blob): return True
    text=html.unescape(blob)
    for pat,fmt in DATE_PATS:
        for m in pat.finditer(text):
            try:
                if fmt=='iso':
                    y,mn,d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    tt=time.mktime((y,mn,d,0,0,0,0,0,-1))
                else:
                    from time import strptime, mktime
                    tt=mktime(time.strptime(m.group(0), fmt))
                if (NOW-tt) <= max_age_days*86400: return True
            except Exception:
                pass
    return False

def collect_recent(index_url, max_pages=6, max_pdfs=60):
    seen={index_url}; q=[index_url]; pdfs=[]
    while q and len(seen)<=max_pages and len(pdfs)<max_pdfs:
        u=q.pop(0)
        try: page=fetch(u)
        except Exception: continue
        # pull links & surrounding text
        blocks = re.split(r'(?i)</?(?:li|div|article|tr)\b', page)
        for blk in blocks:
            for m in re.finditer(r'href=["\']([^"\']+)["\']', blk, re.I):
                href=m.group(1).strip(); link=absu(u, href)
                if link.lower().endswith(".pdf"):
                    if is_recent(blk) or is_recent(link):
                        if link not in pdfs: pdfs.append(link)
                else:
                    if (('page=' in link or 'sort' in link or 'start=' in link or 'view' in link) and
                        urllib.parse.urlparse(link).netloc==urllib.parse.urlparse(index_url).netloc and
                        link not in seen and len(seen)<max_pages):
                        seen.add(link); q.append(link)
    return pdfs[:max_pdfs]

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
            if u not in old:
                f.write(u+"\n"); added+=1
    return added

def harvest_portal(kind):
    # tuned index pages that list new/updated items first
    portals={
        "doj_oip":["https://www.justice.gov/oip/foia-library"],
        "dni_otr":["https://www.dni.gov/index.php/ic-on-the-record"],
        "fbi_vault":[
            "https://vault.fbi.gov/recent-files",   # best-effort listing
            "https://vault.fbi.gov"
        ],
        "cia_rr":[
            "https://www.cia.gov/readingroom/foia-collection",
            "https://www.cia.gov/readingroom"
        ],
        "nsa_foia":[
            "https://www.nsa.gov/foia/reading-room/",
        ]
    }
    urls=portals.get(kind,[])
    found=[]
    for u in urls:
        try:
            found += collect_recent(u, max_pages=6, max_pdfs=60)
        except Exception:
            pass
    added = append_sources(found)
    return {"kind":kind,"found":len(found),"added_to_sources":added}

if __name__=="__main__":
    out=[]
    for k in ["doj_oip","dni_otr","fbi_vault","cia_rr","nsa_foia"]:
        out.append(harvest_portal(k))
    print({"ok":True,"results":out})
