#!/data/data/com.termux/files/usr/bin/python3
import os, json, time, re, html, sqlite3, urllib.request, urllib.parse

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
UA={"User-Agent":"Mozilla/5.0 TornadoAI/1.0","Accept":"application/json"}

ACCOUNT="realDonaldTrump"
BASE="https://truthsocial.com"

def get_json(url, params=None):
    if params: url += "?" + urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def html_to_text(s):
    if not s: return ""
    # remove tags & entities from Mastodon/Soapbox content
    s = re.sub(r"<br\s*/?>","\n", s, flags=re.I)
    s = re.sub(r"</p>","\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>","", s)
    s = html.unescape(s)
    # collapse whitespace
    s = re.sub(r"[ \t]+"," ", s).strip()
    s = re.sub(r"\n{3,}","\n\n", s)
    return s

def upsert_post(c, url, created_at, text):
    ts=int(time.mktime(time.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S")))
    title = (text.split("\n",1)[0] or "(Truth post)")[:120]
    pages = [text] if text else [""]
    # docs
    c.execute("""
      INSERT INTO docs(url,title,content,ts_utc,source_tag,doc_type,page_count)
      VALUES(?,?,?,?,?,?,?)
      ON CONFLICT(url) DO UPDATE SET
        title=excluded.title,
        content=excluded.content,
        ts_utc=excluded.ts_utc,
        source_tag=excluded.source_tag,
        doc_type=excluded.doc_type,
        page_count=excluded.page_count
    """,(url,title,text,ts,"independent","truth",len(pages)))
    # pages
    c.execute("DELETE FROM doc_pages WHERE url=?",(url,))
    for i,p in enumerate(pages, start=1):
        c.execute("INSERT INTO doc_pages(url,page_no,text) VALUES(?,?,?)",(url,i,p))
    # summary (very short)
    snip = text[:400]
    c.execute("""
      INSERT OR REPLACE INTO doc_summaries(url,summary,ts_utc) VALUES(?,?,?)
    """,(url,snip,int(time.time())))

def main():
    # 1) lookup account id
    acct = get_json(f"{BASE}/api/v1/accounts/lookup", {"acct": ACCOUNT})
    acc_id = acct.get("id")
    if not acc_id:
        print(json.dumps({"ok":False,"error":"lookup failed"})); return
    # 2) fetch latest statuses (no token needed)
    statuses = get_json(f"{BASE}/api/v1/accounts/{acc_id}/statuses",
                        {"limit": 40, "exclude_reblogs": "false", "exclude_replies": "false"})
    added=0
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        c.execute("BEGIN IMMEDIATE;")
        for st in statuses:
            # Build a stable canonical URL (their web URL is fine)
            url = st.get("url") or st.get("uri") or f"{BASE}/@{ACCOUNT}/{st.get('id')}"
            created = st.get("created_at","")
            content_html = st.get("content","")
            text = html_to_text(content_html)
            upsert_post(c, url, created, text)
            added += 1
        c.commit()
    print(json.dumps({"ok":True,"account":ACCOUNT,"added":added}))

if __name__=="__main__":
    main()
