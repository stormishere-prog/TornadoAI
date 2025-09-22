#!/data/data/com.termux/files/usr/bin/python3
import os, re, csv, json, sqlite3, argparse, time

DB="corpus.db"
OUT="reports/cases"

def safe(name):
    s=re.sub(r'[^A-Za-z0-9._-]+','_',name).strip('_')
    return s or "Case"

def fetch_case_rows(c, case_name):
    q = """
      SELECT case_name, id, url, page_no, quote, note, tags, status, priority,
             t_start, t_end, ts_utc, title, page_count, doc_sha256
      FROM v_case_bundle
      WHERE case_name = ?
      ORDER BY ts_utc ASC, id ASC
    """
    return c.execute(q,(case_name,)).fetchall()

def to_markdown(case_name, rows):
    now=time.strftime("%Y-%m-%d %H:%M:%S")
    L=[]
    L.append(f"# Case Packet — {case_name}\n")
    L.append(f"_Generated: {now}_\n")
    if not rows:
        L.append("> No evidence yet.\n")
        return "\n".join(L)

    # quick topline
    L.append(f"**Items:** {len(rows)}  |  **First:** {time.strftime('%Y-%m-%d', time.localtime(rows[0][11]))}  |  **Last:** {time.strftime('%Y-%m-%d', time.localtime(rows[-1][11]))}\n")

    # table of contents
    L.append("## Evidence\n")
    for r in rows:
        evid_id=r[1]; title=r[12] or "(untitled)"; pg=r[3] or 1
        L.append(f"- [#{evid_id} · p.{pg}] {title}")

    # detailed entries
    L.append("\n---\n")
    for r in rows:
        (case_name, evid_id, url, page_no, quote, note, tags, status, priority,
         t_start, t_end, ts_utc, title, page_count, doc_sha256) = r

        ts_fmt=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts_utc))
        L.append(f"### #{evid_id} — {title or '(untitled)'}")
        meta = []
        meta.append(f"**URL:** {url}")
        meta.append(f"**Page:** {page_no or 1}/{page_count or '?'}")
        meta.append(f"**When added:** {ts_fmt}")
        if tags: meta.append(f"**Tags:** {tags}")
        if status: meta.append(f"**Status:** {status}")
        if priority is not None: meta.append(f"**Priority:** {priority}")
        if t_start or t_end: meta.append(f"**Clip:** [{t_start or ''} → {t_end or ''}]")
        if doc_sha256: meta.append(f"**Doc SHA256:** `{doc_sha256}`")
        L.append("\n".join(meta))
        if quote:
            L.append("\n> " + quote.replace("\n","\n> "))
        if note:
            L.append(f"\n_Note:_ {note}")
        L.append("\n")

    return "\n".join(L)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="Exact case name (see v_case_bundle)")
    ap.add_argument("--zip", action="store_true", help="Also produce a .zip of the folder")
    args=ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        rows=fetch_case_rows(c, args.case)

    case_dir=os.path.join(OUT, safe(args.case))
    os.makedirs(case_dir, exist_ok=True)

    # Markdown
    md_path=os.path.join(case_dir,"README.md")
    open(md_path,"w",encoding="utf-8").write(to_markdown(args.case, rows))

    # CSV
    csv_path=os.path.join(case_dir,"evidence.csv")
    flds=["evidence_id","url","page","title","quote","note","tags","status","priority","ts_utc","doc_sha256"]
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=flds)
        w.writeheader()
        for r in rows:
            w.writerow({
              "evidence_id": r[1],
              "url": r[2],
              "page": r[3] or 1,
              "title": r[12] or "",
              "quote": r[4] or "",
              "note": r[5] or "",
              "tags": r[6] or "",
              "status": r[7] or "",
              "priority": r[8] if r[8] is not None else "",
              "ts_utc": r[11],
              "doc_sha256": r[14] or ""
            })

    # links.txt
    links_path=os.path.join(case_dir,"links.txt")
    with open(links_path,"w",encoding="utf-8") as f:
        for r in rows:
            f.write(f"{r[2]}\n")

    out={"ok":True,"dir":os.path.abspath(case_dir),"md":os.path.abspath(md_path),"csv":os.path.abspath(csv_path)}
    # Optional zip
    if args.zip:
        import shutil
        zip_path=os.path.join(OUT, safe(args.case) + ".zip")
        if os.path.exists(zip_path): os.remove(zip_path)
        shutil.make_archive(zip_path.replace(".zip",""), "zip", case_dir)
        out["zip"]=os.path.abspath(zip_path)
    print(json.dumps(out))

if __name__=="__main__":
    main()


# --- log packet rebuild --- (alerts_case.log / alerts.jsonl)
try:
    import os, json, time
    # ROOT is already used elsewhere in your tools; fall back to CWD if missing
    try:
        ROOT
    except NameError:
        ROOT = os.getcwd()

    try:
        case_name = args.case
    except Exception:
        case_name = "(unknown)"

    alerts_dir = os.path.join(ROOT, "alerts")
    os.makedirs(alerts_dir, exist_ok=True)

    # plain-text log (easy to tail)
    with open(os.path.join(alerts_dir, "alerts_case.log"), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] rebuilt packet for case={case_name}\n")

    # structured log for machine parsing
    evt = {
        "ts": int(time.time()),
        "event": "case_packet_rebuilt",
        "case": case_name
    }
    with open(os.path.join(alerts_dir, "alerts.jsonl"), "a", encoding="utf-8") as jf:
        jf.write(json.dumps(evt, ensure_ascii=False) + "\n")

except Exception as _log_err:
    # never break packet build because of logging
    pass
