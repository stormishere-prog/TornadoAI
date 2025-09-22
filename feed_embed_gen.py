#!/data/data/com.termux/files/usr/bin/python3
import os, sqlite3, html, time, urllib.parse, collections

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
OUT=os.path.join(ROOT,"www","feed_embed.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def host(u):
    try:
        n=urllib.parse.urlparse(u).netloc.lower()
        return n.lstrip("www.") or "(unknown)"
    except:
        return "(unknown)"

with sqlite3.connect(DB, timeout=30) as c:
    rows = c.execute("""
      SELECT datetime(d.ts_utc,'unixepoch') AS ts,
             IFNULL(d.title,''), IFNULL(s.summary,''), d.url
      FROM docs d LEFT JOIN doc_summaries s ON d.url=s.url
      ORDER BY d.ts_utc DESC
      LIMIT 250
    """).fetchall()

by_host = collections.OrderedDict()
for ts, title, summary, url in rows:
    by_host.setdefault(host(url), []).append((ts or "", title or "", summary or "", url or ""))

PER=10
def card(ts,title,summary,url):
    t=html.escape((title or "(untitled)"))
    s=html.escape(((summary or "").replace("\n"," ").strip())[:240]) or "(no summary yet)"
    u=html.escape(url or "")
    ts=html.escape(ts or "")
    return f'''<article class="card">
  <div class="meta">{ts}</div>
  <h3 class="ttl"><a href="{u}">{t}</a></h3>
  <p class="snip">{s}</p>
  <div class="src">{u}</div>
</article>'''

rows_html=[]
for h,items in list(by_host.items())[:20]:
    cards=''.join(card(*it) for it in items[:PER])
    rows_html.append(f'''
<section class="feedrow">
  <div class="rowhead"><span class="host">{html.escape(h)}</span> <span class="count">({len(items)} new)</span></div>
  <div class="strip nowrap">{cards}</div>
</section>
''')

frag = f'''
<style>
  :root {{ --bg:#0b0f14; --fg:#e8eef6; --muted:#9db0c8; --card:#111722; --border:#1a2636; --accent:#5fb3ff; }}
  .feedrow {{ margin: 14px 0 18px; }}
  .rowhead {{ display:flex; gap:8px; align-items:baseline; padding:2px 6px; color:var(--muted); }}
  .rowhead .host {{ font-weight:600; color:var(--fg); }}
  .rowhead .count {{ font-size:12px; }}
  .strip.nowrap {{ white-space: nowrap; overflow-x: auto; padding: 8px 6px 2px; }}
  .strip.nowrap::-webkit-scrollbar {{ height:8px; }}
  .strip.nowrap::-webkit-scrollbar-thumb {{ background:#213246; border-radius:6px; }}
  .card {{ display:inline-block; vertical-align:top; width:320px; white-space:normal;
          background:var(--card); border:1px solid var(--border); border-radius:14px;
          padding:12px; margin:0 10px 0 0; min-height:140px; }}
  .ttl {{ margin:4px 0 6px; font-size:16px; }}
  .ttl a {{ color:var(--fg); text-decoration:none; }}
  .ttl a:hover {{ color:var(--accent); text-decoration:underline; }}
  .snip {{ color:var(--muted); margin:0 0 8px 0; }}
  .meta {{ color:#8aa0ba; font-size:12px; }}
  .src  {{ color:#88a; font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:100%; }}
</style>
<div class="feed_embed">
  {"".join(rows_html) if rows_html else '<p class="meta">No items yet.</p>'}
</div>
'''
open(OUT,"w",encoding="utf-8").write(frag)
print({"ok": True, "out": OUT})
