#!/data/data/com.termux/files/usr/bin/python3
"""
truth_scrape_html.py
Scrape all public posts from a Truth Social profile by paging HTML pages.
Writes new post URLs into sources.txt and tracks seen ids in truth_state.json.

Notes:
- Uses only Python stdlib.
- Polite default delay between page fetches (SLEEP).
- Caps by MAX_TOTAL posts per run to avoid exploding storage.
"""
import os, time, json, re, urllib.request, urllib.error, urllib.parse, html

ROOT = "/storage/emulated/0/Download/TornadoAI"
ACCOUNT = "realDonaldTrump"                     # change if you want other accounts
BASE = "https://truthsocial.com"
SOURCES = os.path.join(ROOT, "sources.txt")
STATE = os.path.join(ROOT, "truth_state.json")

# Tunables (via env)
MAX_TOTAL = int(os.environ.get("TRUTH_MAX_TOTAL", "200"))   # max posts to add this run
SLEEP = float(os.environ.get("TRUTH_SCRAPE_SLEEP", "0.8"))  # polite delay between page fetches
PER_PAGE_GUESS = 20                                        # pages often show ~20 posts

UA = { "User-Agent": "Mozilla/5.0 (Linux; TornadoAI)" }

# regex to detect post permalinks in HTML (matches /@username/<id> or /notice/<id> style)
POST_RE = re.compile(r'href=["\'](https?://truthsocial\.com/[@A-Za-z0-9_./-]*?/([0-9]+))["\']', re.I)

def ensure_root():
    os.makedirs(ROOT, exist_ok=True)
    if not os.path.exists(SOURCES):
        open(SOURCES,"a",encoding="utf-8").close()

def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE,"r",encoding="utf-8"))
        except:
            pass
    return {"accounts": {}} 

def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)

def fetch_url(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")

def extract_post_links(html_text):
    out=[]
    for m in POST_RE.finditer(html_text):
        full = m.group(1)
        postid = m.group(2)
        # normalize: ensure we have https truthsocial.com/@account/<id>
        # Keep only canonical truthsocial link
        normalized = full.split("#",1)[0]
        out.append((postid, normalized))
    # preserve order and dedupe
    seen=set(); ded=[]
    for pid,url in out:
        if pid in seen: continue
        seen.add(pid); ded.append((pid,url))
    return ded

def canonical_profile_page(account, page):
    # Many Truth Social profiles use /@username or /profiles/..., try both patterns if needed
    return f"{BASE}/@{urllib.parse.quote(account)}?page={page}"

def run_for_account(account):
    st = load_state()
    acc_state = st["accounts"].setdefault(account, {"seen_ids":{}, "last_page":0})
    seen = acc_state["seen_ids"]
    last_page = acc_state.get("last_page", 0)

    added = 0
    page = 1 if last_page==0 else last_page  # resume from where we left last run (conservative)
    consecutive_empty = 0

    while added < MAX_TOTAL:
        url = canonical_profile_page(account, page)
        try:
            body = fetch_url(url)
        except Exception as e:
            # network or blocked; stop cleanly
            break

        posts = extract_post_links(body)
        new_found = 0
        for pid, purl in posts:
            if added >= MAX_TOTAL: break
            if pid in seen: continue
            # append to sources.txt (canonical)
            with open(SOURCES, "a", encoding="utf-8") as f:
                f.write(purl + "\n")
            seen[pid] = int(time.time())
            added += 1; new_found += 1

        # if this page had no new items, increment empty counter and possibly stop
        if new_found == 0:
            consecutive_empty += 1
        else:
            consecutive_empty = 0

        # prepare next iteration: stop if too many consecutive empty pages (no more old posts)
        if consecutive_empty >= 3:
            page += 1
            acc_state["last_page"] = page
            break

        page += 1
        acc_state["last_page"] = page
        time.sleep(SLEEP)

    # save state
    st["accounts"][account] = acc_state
    save_state(st)
    return {"ok": True, "account": account, "added": added, "next_page": acc_state.get("last_page", page)}

def main():
    ensure_root()
    res = run_for_account(ACCOUNT)
    print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
