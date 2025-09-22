#!/data/data/com.termux/files/usr/bin/python3
import os, sys, sqlite3, argparse, time, csv, math
from urllib.parse import urlparse
from collections import defaultdict, Counter

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT, "corpus.db")
OUTDIR=os.path.join(ROOT, "reports")
os.makedirs(OUTDIR, exist_ok=True)

AGENCY_MAP = [
  ("cia.gov",        "CIA"),
  ("vault.fbi.gov",  "FBI"),
  ("fbi.gov",        "FBI"),
  ("justice.gov",    "DOJ"),
  ("dni.gov",        "DNI"),
  ("nsa.gov",        "NSA"),
  ("archives.gov",   "NARA"),
  ("whitehouse.gov", "White House"),
]

def agency_for(netloc:str)->str:
  host = netloc.lower()
  for needle, label in AGENCY_MAP:
    if needle in host:
      return label
  return "Other"

def mk_view(c:sqlite3.Connection):
  # Convenience view (no-op if already exists)
  c.executescript("""
  CREATE VIEW IF NOT EXISTS v_propaganda_pages AS
  SELECT p.url, p.page_no, p.text,
         p.propaganda_score, p.propaganda_label, p.propaganda_notes,
         d.title, d.ts_utc
  FROM doc_pages p
  JOIN docs d ON d.url = p.url;
  """)

def fetch_rows(c, min_score, days):
  params = [min_score]
  where = ["propaganda_score IS NOT NULL", "propaganda_score >= ?"]
  if days is not None and days > 0:
    cutoff = int(time.time()) - days*86400
    where.append("d.ts_utc >= ?")
    params.append(cutoff)

  q = f"""
    SELECT p.url, p.page_no, IFNULL(p.propaganda_score,0) AS score,
           IFNULL(p.propaganda_label,'') AS label,
           IFNULL(d.title,'') AS title,
           IFNULL(d.ts_utc,0) AS ts
    FROM doc_pages p
    JOIN docs d ON d.url = p.url
    WHERE {' AND '.join(where)}
  """
  c.row_factory = sqlite3.Row
  return c.execute(q, params).fetchall()

def dt(ts): 
  return time.strftime("%Y-%m-%d", time.localtime(ts or 0))

def main():
  ap = argparse.ArgumentParser(description="Build propaganda risk map report.")
  ap.add_argument("--min", type=float, default=0.6, help="Minimum propaganda_score to count (default 0.6)")
  ap.add_argument("--days", type=int, default=90, help="Lookback window in days (default 90; 0 = all time)")
  ap.add_argument("--top-pages", type=int, default=20, help="Max top risky pages in report")
  args = ap.parse_args()

  # open DB (with a bit of patience)
  def _conn():
    delay=0.2
    for _ in range(8):
      try:
        cx = sqlite3.connect(DB, timeout=30)
        cx.execute("PRAGMA busy_timeout=6000;")
        return cx
      except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
          time.sleep(delay); delay=min(delay*1.8,3.0)
          continue
        raise
    return sqlite3.connect(DB, timeout=30)

  with _conn() as c:
    mk_view(c)
    rows = fetch_rows(c, args.min, None if args.days==0 else args.days)

  if not rows:
    print({"ok": True, "message":"no rows above threshold", "items":0})
    return

  # Aggregations
  by_domain = Counter()
  by_agency = Counter()
  domain_scores = defaultdict(list)
  agency_scores = defaultdict(list)
  trend = Counter()  # by date
  top_pages = []

  for r in rows:
    parsed = urlparse(r["url"])
    dom = parsed.netloc.lower()
    agen = agency_for(dom)
    score = float(r["score"])
    by_domain[dom] += 1
    by_agency[agen] += 1
    domain_scores[dom].append(score)
    agency_scores[agen].append(score)
    trend[dt(r["ts"])] += 1
    top_pages.append((score, r["url"], r["page_no"], r["title"]))

  # Sort & slice
  def avg(lst): return sum(lst)/len(lst) if lst else 0.0
  dom_table = sorted([(dom, cnt, avg(domain_scores[dom])) for dom, cnt in by_domain.items()],
                     key=lambda x:(-x[1], -x[2]))[:50]
  ag_table  = sorted([(ag, cnt, avg(agency_scores[ag])) for ag, cnt in by_agency.items()],
                     key=lambda x:(-x[1], -x[2]))
  trend_table = sorted(trend.items())[-60:]  # last 60 days shown (or fewer)
  top_pages = sorted(top_pages, key=lambda x: (-x[0]))[:args.top_pages]

  # Write CSV
  csv_path = os.path.join(OUTDIR, "propaganda_risk.csv")
  with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["domain","count","avg_score"])
    for dom, cnt, av in dom_table:
      w.writerow([dom, cnt, f"{av:.3f}"])
    w.writerow([])
    w.writerow(["agency","count","avg_score"])
    for ag, cnt, av in ag_table:
      w.writerow([ag, cnt, f"{av:.3f}"])
    w.writerow([])
    w.writerow(["date","count"])
    for d, cnt in trend_table:
      w.writerow([d, cnt])
    w.writerow([])
    w.writerow(["score","url","page","title"])
    for sc, url, page, title in top_pages:
      w.writerow([f"{sc:.3f}", url, page, title])

  # Write Markdown
  md_path = os.path.join(OUTDIR, "propaganda_risk.md")
  lines=[]
  lines.append(f"# Propaganda Risk Map")
  lines.append("")
  lines.append(f"- **Lookback:** {('all time' if args.days==0 else f'last {args.days} days')}")
  lines.append(f"- **Threshold:** score ≥ {args.min}")
  lines.append(f"- **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
  lines.append("")
  lines.append("## Top Domains")
  lines.append("")
  lines.append("| Domain | Items | Avg Score |")
  lines.append("|---|---:|---:|")
  for dom, cnt, av in dom_table:
    lines.append(f"| `{dom}` | {cnt} | {av:.3f} |")
  lines.append("")
  lines.append("## By Agency Family")
  lines.append("")
  lines.append("| Agency | Items | Avg Score |")
  lines.append("|---|---:|---:|")
  for ag, cnt, av in ag_table:
    lines.append(f"| {ag} | {cnt} | {av:.3f} |")
  lines.append("")
  lines.append("## Trend (daily count above threshold)")
  lines.append("")
  if trend_table:
    lines.append("| Date | Count |")
    lines.append("|---|---:|")
    for d, cnt in trend_table:
      lines.append(f"| {d} | {cnt} |")
  else:
    lines.append("_No data in selected window._")
  lines.append("")
  lines.append("## Top Pages")
  lines.append("")
  for sc, url, page, title in top_pages:
    lines.append(f"- **{title or '(untitled)'}** — p.{page} — score {sc:.3f}  \n  {url}")
  lines.append("")
  open(md_path,"w",encoding="utf-8").write("\n".join(lines))

  print({"ok": True, "items": len(rows), "csv": csv_path, "md": md_path})

if __name__=="__main__":
  main()
