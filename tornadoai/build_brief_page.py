#!/data/data/com.termux/files/usr/bin/python3
import os, time, sqlite3, html, re

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
WWW=os.path.join(ROOT,"www")
OUT=os.path.join(WWW,"daily_brief.html")
os.makedirs(WWW, exist_ok=True)
SINCE=int(time.time())-24*3600

Q = """
SELECT
  CAST(d.ts_utc AS INTEGER)          AS ts,
  IFNULL(s.summary, IFNULL(dp.content, IFNULL(d.content,''))) AS body,
  IFNULL(d.title,'')                  AS title,
  IFNULL(d.doc_type,'')               AS dtype,
  IFNULL(d.source_tag,'')             AS tag,
  d.url                               AS url
FROM docs d
LEFT JOIN doc_pages     dp ON dp.url=d.url AND dp.page_no=1
LEFT JOIN doc_summaries s  ON s.url=d.url
WHERE d.ts_utc >= ?
ORDER BY d.ts_utc DESC
LIMIT 400
"""

def esc(s): return html.escape(s or "")
def autolink(t): return re.sub(r'(https?://\S+)', r'<a href="\\1">\\1</a>', t or "")
def paras(txt):
    txt=(txt or "").strip()
    if not txt: return "<p class='empty'>(no content)</p>"
    return "\n".join(f"<p>{autolink(esc(p.strip()))}</p>" for p in txt.splitlines() if p.strip())

with sqlite3.connect(DB, timeout=60) as c:
    c.row_factory = sqlite3.Row
    rows = c.execute(Q, (SINCE,)).fetchall()

def card(r):
    ts = int(r["ts"]) if str(r["ts"]).isdigit() else int(time.time())
    dt = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
    return f"""
<article class="card">
  <div class="meta">{dt}</div>
  <h3 class="ttl"><a href="{esc(r['url'])}">{esc(r['title']) or '(untitled)'}</a></h3>
  <div class="chips">
    {f"<span class='chip'>{esc(r['dtype'])}</span>" if r['dtype'] else ""}
    {f"<span class='chip'>{esc(r['tag'])}</span>" if r['tag'] else ""}
  </div>
  <div class="body">{paras(r['body'])}</div>
  <div class="src">{esc(r['url'])}</div>
</article>
"""

cards = "".join(card(r) for r in rows)

page = f"""<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TornadoAI — Daily Brief</title>
<style>
:root {{ --bg:#0b0f14; --fg:#e8eef6; --muted:#9db0c8; --card:#111722; --border:#1a2636; --accent:#5fb3ff; }}
*{{box-sizing:border-box}} body{{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial;background:var(--bg);color:var(--fg)}}
header{{position:sticky;top:0;padding:12px 10px;border-bottom:1px solid var(--border);background:#0b0f14f2;backdrop-filter:blur(6px)}}
.tabs a{{margin-right:10px;padding:6px 10px;border:1px solid var(--border);border-radius:10px;text-decoration:none;color:var(--fg)}}
.tabs a.active{{background:#142033}}
main{{padding:12px 10px 24px;max-width:1100px;margin:0 auto}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px;min-height:140px}}
.ttl{{margin:6px 0 8px;font-size:16px}} .ttl a{{color:var(--fg);text-decoration:none}} .ttl a:hover{{color:var(--accent);text-decoration:underline}}
.meta{{color:#8aa0ba;font-size:12px}} .src{{color:#88a;font-size:12px;margin-top:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.chips{{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 8px}} .chip{{font-size:12px;padding:2px 6px;border-radius:10px;border:1px solid var(--border);opacity:.9}}
footer{{color:var(--muted);text-align:center;padding:18px;font-size:13px}}
</style>
<header>
  <div class="tabs">
    <a href="chat_panel.html">Chat</a>
    <a href="feed_embed.html">Feed</a>
    <a class="active" href="daily_brief.html">Brief</a>
  </div>
  <div class="summary">Last 24 hours • Generated {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
</header>
<main>
  <section class="grid">
    {cards or '<p class="summary">No items in last 24h.</p>'}
  </section>
</main>
<footer>Built by TornadoAI</footer>
"""
open(OUT,"w",encoding="utf-8").write(page)
print({"ok": True, "wrote": OUT})
