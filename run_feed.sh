#!/data/data/com.termux/files/usr/bin/sh
set -e
ROOT="/storage/emulated/0/Download/TornadoAI"
LOG="$ROOT/harvester.log"
cd "$ROOT"

echo "[run_feed] $(date '+%F %T') starting" >>"$LOG"

# X via your x_proxy (already working)
X_REQUEST_DELAY="${X_REQUEST_DELAY:-4.0}" sh ./safe_run.sh python3 x_fetch_xproxy.py >>"$LOG" 2>&1 || true

# Truth Social pull (best-effort; skip on error)
sh ./safe_run.sh python3 truth_pull_public.py >>"$LOG" 2>&1 || true

# Summaries/tags/echo/contradictions + reports
sh ./safe_run.sh python3 news_summarize.py >>"$LOG" 2>&1 || true
sh ./post_ingest.sh >>"$LOG" 2>&1 || true

# Rebuild the feed page (last 48h, grouped by source)
python3 - <<'PY' >>"$LOG" 2>&1 || true
import os, sqlite3, html, time, urllib.parse, collections
ROOT="/storage/emulated/0/Download/TornadoAI"; DB=os.path.join(ROOT,"corpus.db")
OUT=os.path.join(ROOT,"www","feed_embed.html"); os.makedirs(os.path.dirname(OUT), exist_ok=True)
def host(u):
    try: n=urllib.parse.urlparse(u).netloc.lower(); return n.lstrip("www.") or "(unknown)"
    except: return "(unknown)"
now=int(time.time()); since=now-48*3600
with sqlite3.connect(DB, timeout=30) as c:
    rows=c.execute("""
      SELECT d.ts_utc, IFNULL(d.title,''), IFNULL(s.summary,''), d.url,
             IFNULL(d.source_tag,''), IFNULL(d.doc_type,''), IFNULL(d.content,'')
      FROM docs d LEFT JOIN doc_summaries s ON d.url=s.url
      WHERE d.ts_utc >= ?
      ORDER BY d.ts_utc DESC
      LIMIT 500
    """,(since,)).fetchall()
by_host=collections.OrderedDict()
for ts,title,summary,url,tag,dtype,content in rows:
    body = summary or content or title
    by_host.setdefault(host(url), []).append((ts,title,body,url,tag,dtype))
def esc(s): return html.escape((s or "").strip())
def t(ts): 
    try: return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ts)))
    except: return ""
def chip(txt, cls): return f'<span class="chip {cls}">{esc(txt)}</span>' if txt else ""
def card(ts,title,body,url,tag,dtype):
    ttl= esc(title) or "(untitled)"; snip=esc((body or "").replace("\n"," "))[:300] or "(no summary yet)"
    u=esc(url)
    return f'''<article class="card">
  <div class="meta">{t(ts)}</div>
  <h3 class="ttl"><a href="{u}">{ttl}</a></h3>
  <p class="snip">{snip}</p>
  <div class="chips">
    {chip(dtype or "?", "dt-"+(dtype or "q"))}
    {chip(tag or "unknown", "tag-"+(tag.split('_',1)[0] if tag else "unknown"))}
  </div>
  <div class="src">{u}</div>
</article>'''
rows_html=[]
for h,items in list(by_host.items())[:24]:
    cards=''.join(card(*it) for it in items[:12])
    rows_html.append(f'''
<section class="feedrow">
  <div class="rowhead"><span class="host">{esc(h)}</span> <span class="count">({len(items)} new)</span></div>
  <div class="strip nowrap">{cards}</div>
</section>''')
page=f'''<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TornadoAI — Feed</title>
<style>
  :root{{--bg:#0b0f14;--fg:#e8eef6;--muted:#9db0c8;--card:#111722;--border:#1a2636;--accent:#5fb3ff}}
  *{{box-sizing:border-box}} body{{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial;background:var(--bg);color:var(--fg)}}
  header{{position:sticky;top:0;padding:12px 10px;border-bottom:1px solid var(--border);background:#0b0f14f2;backdrop-filter:blur(6px)}}
  .tabs a{{margin-right:10px;padding:6px 10px;border:1px solid var(--border);border-radius:10px;text-decoration:none;color:var(--fg)}}
  .tabs a.active{{background:#142033}}
  main{{padding:12px 10px 20px;max-width:1100px;margin:0 auto}}
  .feedrow{{margin:14px 0 18px}}
  .rowhead{{display:flex;gap:8px;align-items:baseline;padding:2px 6px;color:var(--muted)}}
  .rowhead .host{{font-weight:600;color:var(--fg)}}
  .strip.nowrap{{white-space:nowrap;overflow-x:auto;padding:8px 6px 2px}}
  .strip.nowrap::-webkit-scrollbar{{height:8px}} .strip.nowrap::-webkit-scrollbar-thumb{{background:#213246;border-radius:6px}}
  .card{{display:inline-block;vertical-align:top;width:320px;white-space:normal;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px;margin:0 10px 0 0;min-height:140px}}
  .ttl{{margin:4px 0 6px;font-size:16px}} .ttl a{{color:var(--fg);text-decoration:none}} .ttl a:hover{{color:var(--accent);text-decoration:underline}}
  .snip{{color:var(--muted);margin:0 0 8px 0}}
  .meta{{color:#8aa0ba;font-size:12px}}
  .src{{color:#88a;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}}
  .chips{{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 0}}
  .chip{{font-size:12px;padding:2px 6px;border-radius:10px;border:1px solid var(--border);opacity:.9}}
  .chip.dt-x{{background:#1b2a40}} .chip.dt-truth{{background:#2a1b40}} .chip.dt-pdf{{background:#402a1b}} .chip.dt-html{{background:#1b4031}}
  .chip.tag-official{{background:#1b3b2a}} .chip.tag-independent{{background:#2a2f40}} .chip.tag-propaganda{{background:#402626}} .chip.tag-unknown{{background:#2a2a2a}}
  footer{{color:var(--muted);text-align:center;padding:18px;font-size:13px}}
</style>
<header>
  <div class="tabs">
    <a href="chat_panel.html">Chat</a>
    <a class="active" href="feed_embed.html">Feed</a>
  </div>
</header>
<main>
  {'\\n'.join(rows_html) if rows_html else '<p class="meta">No items in last 48h.</p>'}
</main>
<footer>Built {time.strftime('%Y-%m-%d %H:%M:%S')}</footer>
'''
open(OUT,"w",encoding="utf-8").write(page)
PY

# do not auto-open; this runs headless for scheduler
echo "[run_feed] $(date '+%F %T') done" >>"$LOG"
