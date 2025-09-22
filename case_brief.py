#!/data/data/com.termux/files/usr/bin/python3
import os, sys, sqlite3, argparse, time, textwrap, hashlib

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
OUT=os.path.join(ROOT,"reports")
os.makedirs(OUT, exist_ok=True)

def md_escape(s): 
    return s.replace("<","&lt;").replace(">","&gt;")

def brief_for_case(c, case_name:str, limit:int=None):
    q = """
      SELECT e.id, e.url, e.page_no, e.quote, e.note, e.tags, e.ts_utc,
             IFNULL(d.title,'') AS title, IFNULL(d.page_count,0) AS page_count
      FROM v_case_bundle e
      WHERE case_name = ?
      ORDER BY e.priority DESC, e.ts_utc DESC, e.id DESC
    """
    rows = c.execute(q,(case_name,)).fetchall()
    if limit: rows = rows[:limit]
    if not rows: return None, None

    # brief header
    fn_base = case_name.lower().replace("/","_").replace(" ","_")
    out_path = os.path.join(OUT, f"{fn_base}.md")

    lines=[]
    lines.append(f"# Case Brief — {case_name}")
    lines.append("")
    lines.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}_")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for r in rows:
        ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r["ts_utc"] or 0))
        title = r["title"] or "(untitled)"
        quote = (r["quote"] or "").strip()
        if len(quote) > 800:
            quote = quote[:780] + " ..."
        # stable ref id (hash)
        ref = hashlib.sha1(f'{r["url"]}|{r["page_no"]}|{r["id"]}'.encode()).hexdigest()[:10]
        lines.append(f"### {title} — p.{r['page_no']}  \n`[{ref}]`")
        lines.append(f"- **When saved:** {ts}")
        if r["tags"]:
            lines.append(f"- **Tags:** {md_escape(r['tags'])}")
        if r["note"]:
            lines.append(f"- **Note:** {md_escape(r['note'])}")
        lines.append(f"- **Source:** {r['url']}")
        lines.append("")
        lines.append("> " + md_escape(quote))
        lines.append("")
    open(out_path,"w",encoding="utf-8").write("\n".join(lines))
    return out_path, len(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="Case name (exact)")
    ap.add_argument("--limit", type=int, default=None, help="Max items")
    args = ap.parse_args()

    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        # ensure views exist (no-op if already)
        c.executescript("""
          CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY, name TEXT UNIQUE, note TEXT, created_utc INTEGER);
          CREATE TABLE IF NOT EXISTS case_evidence(case_id INTEGER, evidence_id INTEGER, added_utc INTEGER, PRIMARY KEY(case_id,evidence_id));
        """)
        path, n = brief_for_case(c, args.case, args.limit)
        if not path:
            print({"ok": False, "message":"no evidence for case"})
            sys.exit(0)
        print({"ok": True, "path": path, "items": n})

if __name__=="__main__":
    main()
