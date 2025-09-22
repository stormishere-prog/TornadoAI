#!/data/data/com.termux/files/usr/bin/python3
import re, os, time, html, urllib.parse, urllib.request, argparse

ROOT="/storage/emulated/0/Download/TornadoAI"
SRC=os.path.join(ROOT,"sources.txt")
UA={"User-Agent":"Mozilla/5.0"}
NOW=time.time()

def fetch(u, timeout=25):
    req=urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","ignore")

def absu(base, href): return urllib.parse.urljoin(base, href)

def same_host(a,b):
    pa=urllib.parse.urlparse(a); pb=urllib.parse.urlparse(b)
    return (pa.scheme,pa.netloc)==(pb.scheme,pb.netloc)

# quick “recent” hint: prioritize blocks with 2024/2025 or obvious dates
Y_PAT=re.compile(r'\b(2024|2025)\b')
def is_recentish(txt:str):
    if Y_PAT.search(txt): return True
    if re.search(r'\b(20\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12]\d|3[01])\b', txt): return True
    if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}', txt, re.I): return True
    return False

def extract_links(page_html, base):
    out=[]
    for m in re.finditer(r'href=["\']([^"\']+)["\']', page_html, re.I):
        out.append(absu(base, m.group(1)))
    return out

def looks_item_url(kind, url):
    u = url.lower()
    if kind == "fbi_vault":
        return "vault.fbi.gov" in u and "/vault/" in u and not u.endswith(".pdf")
    if kind == "cia_rr":
        return ("cia.gov" in u) and ("/readingroom/" in u) and not u.endswith(".pdf")
    if kind == "dni_otr":
        return ("dni.gov" in u) and ("/ic-on-the-record" in u or "/newsroom/" in u or "/dig" in u or "/news" in u) and not u.endswith(".pdf")
    if kind == "nsa_foia":
        return ("nsa.gov" in u) and ("/foia" in u or "/reading-room" in u) and not u.endswith(".pdf")
    if kind == "doj_oip":
        return ("justice.gov" in u) and ("oip" in u or "foia" in u) and not u.endswith(".pdf")
    if kind == "nara_aad":
        return ("aad.archives.gov" in u) and ("series" in u or "results" in u or "detail" in u)
    return False

def maybe_pdf_link(url):
    u = url.lower()
    if u.endswith(".pdf"):
        return True
    # links that often serve PDFs without .pdf suffix
    hints = ("/download/file/","/sites/default/files/","application/pdf",
             "view=1&inline=1","attachment","att","file=","files/","asset?sid=")
    return any(h in u for h in hints)

def is_pdf_bytes(url, timeout=12):
    # try to read first bytes; many servers accept Range but we fall back to a tiny GET
    try:
        req=urllib.request.Request(url, headers={**UA, "Range":"bytes=0-7"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b=r.read(8)
        return b[:4].lower()==b"%pdf"
    except Exception:
        # second chance small GET
        try:
            req=urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b=r.read(8)
            return b[:4].lower()==b"%pdf"
        except Exception:
            return False

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

def crawl(kind, list_urls, max_list_pages=12, max_items=150, max_pdfs=200):
    item_pages=[]; pdfs=[]
    seen=set()

    # 1) walk listing pages, collect item-page links (keep order)
    for start in list_urls:
        q=[start]; hops=0
        while q and hops<max_list_pages and len(item_pages)<max_items:
            u=q.pop(0); hops+=1
            try: page=fetch(u)
            except Exception: continue
            # prioritize recent-ish blocks by splitting on common containers
            blocks=re.split(r'(?i)</?(?:li|div|article|tr|p)\b', page)
            for blk in blocks:
                # direct PDFs on list (rare but possible)
                for m in re.finditer(r'href=["\']([^"\']+)["\']', blk, re.I):
                    link=absu(u, m.group(1))
                    if link.lower().endswith(".pdf") and link not in pdfs:
                        pdfs.append(link)
                # item pages we need to open
                for m in re.finditer(r'href=["\']([^"\']+)["\']', blk, re.I):
                    link=absu(u, m.group(1))
                    if same_host(start, link) and looks_item_url(kind, link):
                        if link not in item_pages:
                            if not is_recentish(blk):
                                # keep, but recent-ish go first
                                item_pages.append(link)
                            else:
                                item_pages.insert(0, link)
                # pagination “next”
                if re.search(r'>\s*(Next|Older|More)\s*<', blk, re.I):
                    for m2 in re.finditer(r'href=["\']([^"\']+)["\']', blk, re.I):
                        nxt=absu(u, m2.group(1))
                        if same_host(start, nxt) and nxt not in q and nxt not in seen:
                            q.append(nxt); seen.add(nxt)
            seen.add(u)

    # cap item pages
    item_pages=item_pages[:max_items]

    # 2) open each item page, harvest PDFs inside
    for it in item_pages:
        if len(pdfs)>=max_pdfs: break
        try: html_page=fetch(it)
        except Exception: continue
        # obvious .pdf
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html_page, re.I):
            link=absu(it, m.group(1))
            if maybe_pdf_link(link):
                if link.lower().endswith(".pdf"):
                    if link not in pdfs: pdfs.append(link)
                else:
                    # verify by sniffing bytes (cheap)
                    if is_pdf_bytes(link):
                        if link not in pdfs: pdfs.append(link)
        # some sites expose “@@download/file/…” forms; already caught by maybe_pdf_link()

    # dedupe & limit
    pdfs=list(dict.fromkeys(pdfs))[:max_pdfs]
    added = append_sources(pdfs)
    return {"kind":kind, "found":len(pdfs), "added_to_sources":added}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit-items", type=int, default=150)
    ap.add_argument("--limit-pdfs", type=int, default=200)
    ap.add_argument("--list-pages", type=int, default=12)
    args=ap.parse_args()

    portals = {
  "doj_oip": [
    "https://www.justice.gov/oip/foia-library",
    "https://www.justice.gov/oip",
  ],
  "dni_otr": [
    "https://www.dni.gov/index.php/ic-on-the-record",
    "https://www.dni.gov/index.php/newsroom/press-releases",
    "https://www.dni.gov/index.php/newsroom/dig",
  ],
  "fbi_vault": [
    "https://vault.fbi.gov/recently-added",
    "https://vault.fbi.gov/recent-files",
    "https://vault.fbi.gov/",
  ],
  "cia_rr": [
    "https://www.cia.gov/readingroom/search/site/?f%5B0%5D=ds_created%3A%5B2025-01-01T00%3A00%3A00Z%20TO%202026-01-01T00%3A00%3A00Z%5D",
    "https://www.cia.gov/readingroom/foia-collection",
    "https://www.cia.gov/readingroom",
  ],
  "nsa_foia": [
    "https://www.nsa.gov/foia/reading-room/",
  ],
  "nara_aad": [
    "https://aad.archives.gov/aad/series-list.jsp?cat=TS19",
  ],
}

    results=[]
    for kind, lists in portals.items():
        results.append(crawl(kind, lists,
                             max_list_pages=args.list_pages,
                             max_items=args.limit_items,
                             max_pdfs=args.limit_pdfs))
    print({"ok":True,"results":results})

if __name__=="__main__": main()
