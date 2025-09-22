#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, time, sys
import urllib.request
import re
import xml.etree.ElementTree as ET

DB = "corpus.db"
FEED = "https://www.whitehouse.gov/presidential-actions/feed/"

def clean_html(s):
    # strip tags
    return re.sub(r'<[^>]+>', ' ', s or '').strip()

def fetch_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

def parse_feed(data):
    items = []
    root = ET.fromstring(data)
    # find all item elements
    for it in root.findall('.//item'):
        title_el = it.find('title')
        link_el = it.find('link')
        desc_el = it.find('description')
        pub_el = it.find('pubDate')
        title = title_el.text.strip() if title_el is not None else ""
        link = link_el.text.strip() if link_el is not None else ""
        desc = desc_el.text.strip() if desc_el is not None else ""
        pub = pub_el.text.strip() if pub_el is not None else ""
        items.append((title, link, desc, pub))
    return items

def main():
    with sqlite3.connect(DB) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        c.execute("BEGIN IMMEDIATE;")
        added = 0
        try:
            data = fetch_feed(FEED)
            for (title, link, desc, pub) in parse_feed(data):
                content = clean_html(desc) or clean_html(title)
                if not content:
                    continue
                url = link
                ts = int(time.time())
                # insert
                c.execute("""
                  INSERT OR IGNORE INTO docs(url, title, content, ts_utc, source_trust, sha256)
                  VALUES(?,?,?,?,?,?)
                """, (url, title, content, ts, 70, ""))
                added += c.total_changes
            c.execute("COMMIT;")
        except Exception as e:
            c.execute("ROLLBACK;")
            print({"error": str(e)}, file=sys.stderr)
            sys.exit(1)
    print({"ok":True, "added":added})

if __name__=="__main__":
    main()
