#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, csv, pathlib, datetime as dt
ROOT = "/storage/emulated/0/Download/TornadoAI"
ALERTS = os.path.join(ROOT, "alerts", "alerts.jsonl")
OUTDIR = os.path.join(ROOT, "reports", "alerts")
os.makedirs(OUTDIR, exist_ok=True)

# window: last 24h (override via --hours N)
hours = 24
for i,arg in enumerate(sys.argv):
    if arg == "--hours" and i+1 < len(sys.argv):
        hours = int(sys.argv[i+1])

cut = int(time.time()) - hours*3600
items = []
if os.path.exists(ALERTS):
    with open(ALERTS, "r", encoding="utf-8") as f:
        for ln in f:
            try:
                ev = json.loads(ln)
                if ev.get("ts", 0) >= cut:
                    items.append(ev)
            except: pass

# group by event + tag/case
def key(ev):
    return (ev.get("event","?"), ev.get("tag") or ev.get("case") or "")

groups = {}
for ev in items:
    groups.setdefault(key(ev), []).append(ev)

# filenames
stamp = dt.datetime.now().strftime("%Y%m%d")
md_path = os.path.join(OUTDIR, f"alerts_{stamp}.md")
csv_path = os.path.join(OUTDIR, f"alerts_{stamp}.csv")

# write CSV
with open(csv_path, "w", newline="", encoding="utf-8") as cf:
    w = csv.writer(cf)
    w.writerow(["ts_iso","event","tag","case","priority","query","url","page","snippet"])
    for ev in items:
        ts_iso = dt.datetime.fromtimestamp(ev.get("ts",0)).isoformat(sep=" ")
        w.writerow([
            ts_iso,
            ev.get("event",""),
            ev.get("tag",""),
            ev.get("case",""),
            ev.get("priority",""),
            ev.get("query",""),
            ev.get("url",""),
            ev.get("page",""),
            (ev.get("snippet","") or "").replace("\n"," ")[:300]
        ])

# write Markdown summary
with open(md_path, "w", encoding="utf-8") as mf:
    mf.write(f"# Alerts (last {hours}h) — {stamp}\n\n")
    if not items:
        mf.write("_No alerts in window._\n")
    else:
        # top line
        mf.write(f"- Total alerts: **{len(items)}**\n")
        # by bucket
        mf.write("\n## Buckets\n")
        for (evt, bucket), lst in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
            title = bucket or "(no tag/case)"
            mf.write(f"- **{evt}** / **{title}** — {len(lst)}\n")
        # details
        mf.write("\n## Details\n")
        for ev in items:
            ts_iso = dt.datetime.fromtimestamp(ev.get("ts",0)).isoformat(sep=" ")
            title = ev.get("tag") or ev.get("case") or "(untagged)"
            url = ev.get("url","")
            snip = (ev.get("snippet","") or "").strip().replace("\n"," ")
            page = ev.get("page")
            mf.write(f"- [{ts_iso}] **{ev.get('event','')}** — **{title}**")
            if page: mf.write(f" (p.{page})")
            if url: mf.write(f" — {url}")
            if snip: mf.write(f"\n  \n  > {snip[:400]}\n")
            else: mf.write("\n")

print({"ok": True, "items": len(items), "md": md_path, "csv": csv_path})
