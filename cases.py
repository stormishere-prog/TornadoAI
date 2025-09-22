#!/data/data/com.termux/files/usr/bin/python3
import os, sys, sqlite3, argparse, json, time

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA foreign_keys=ON;")
    return c

def ensure_views():
    # Views/columns were created earlier, but be tolerant:
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS cases(
          id INTEGER PRIMARY KEY,
          name TEXT UNIQUE,
          note TEXT,
          created_utc INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS case_evidence(
          case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
          evidence_id INTEGER REFERENCES evidence(id) ON DELETE CASCADE,
          added_utc INTEGER DEFAULT (strftime('%s','now')),
          PRIMARY KEY (case_id, evidence_id)
        );
        """)
        # v_evidence_full + v_case_bundle should already exist; skip if present
        # (No-op if they exist)
        try:
            c.execute("SELECT 1 FROM v_evidence_full LIMIT 1;")
            c.execute("SELECT 1 FROM v_case_bundle  LIMIT 1;")
        except sqlite3.OperationalError:
            pass

def new_case(name, note):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO cases(name,note) VALUES(?,?)", (name, note or ""))
        row = c.execute("SELECT id,name,note,created_utc FROM cases WHERE name=?", (name,)).fetchone()
    return {"ok": True, "case": {"id": row[0], "name": row[1], "note": row[2], "created_utc": row[3]}}

def list_cases():
    with conn() as c:
        rows = c.execute("SELECT id,name,note,datetime(created_utc,'unixepoch') FROM cases ORDER BY created_utc DESC").fetchall()
    return {"ok": True, "cases": [{"id":r[0], "name":r[1], "note":r[2], "created":r[3]} for r in rows]}

def attach(case, evidence_ids):
    with conn() as c:
        cid = c.execute("SELECT id FROM cases WHERE name=? OR id=?", (case, case)).fetchone()
        if not cid: return {"ok":False, "error":"case not found"}
        cid = cid[0]
        added = 0
        for eid in evidence_ids:
            try:
                c.execute("INSERT OR IGNORE INTO case_evidence(case_id,evidence_id) VALUES(?,?)",(cid,int(eid)))
                added += c.rowcount if hasattr(c, "rowcount") else 0
            except Exception: pass
    return {"ok":True, "attached": len(evidence_ids)}

def detach(case, evidence_ids):
    with conn() as c:
        cid = c.execute("SELECT id FROM cases WHERE name=? OR id=?", (case, case)).fetchone()
        if not cid: return {"ok":False, "error":"case not found"}
        cid = cid[0]
        removed = 0
        for eid in evidence_ids:
            c.execute("DELETE FROM case_evidence WHERE case_id=? AND evidence_id=?", (cid,int(eid)))
            removed += c.rowcount if hasattr(c, "rowcount") else 0
    return {"ok":True, "removed": removed}

def show_case(case, limit):
    with conn() as c:
        cid = c.execute("SELECT id,name FROM cases WHERE name=? OR id=?", (case, case)).fetchone()
        if not cid: return {"ok":False, "error":"case not found"}
        cname = cid[1]
        rows = c.execute("""
          SELECT e.id, e.url, e.page_no, e.title, e.quote, e.tags, e.status, e.priority,
                 e.t_start, e.t_end, datetime(e.ts_utc,'unixepoch')
          FROM v_case_bundle e
          WHERE case_name=? ORDER BY e.ts_utc DESC LIMIT ?;
        """, (cname, limit)).fetchall()
    out = []
    for r in rows:
        out.append({
          "evidence_id": r[0], "url": r[1], "page": r[2], "title": r[3] or "",
          "quote": r[4] or "", "tags": r[5] or "", "status": r[6] or "open",
          "priority": r[7] or 0, "t_start": r[8], "t_end": r[9], "ts": r[10]
        })
    return {"ok": True, "case": cname, "hits": out}

def export_md(case, outfile=None):
    with conn() as c:
        cid = c.execute("SELECT id,name,note,datetime(created_utc,'unixepoch') FROM cases WHERE name=? OR id=?",(case,case)).fetchone()
        if not cid: return {"ok":False, "error":"case not found"}
        cname, cnote, ccreated = cid[1], cid[2], cid[3]
        rows = c.execute("""
          SELECT e.id, e.url, e.page_no, e.title, e.quote, e.tags, e.status, e.priority,
                 e.t_start, e.t_end, datetime(e.ts_utc,'unixepoch'), e.doc_sha256
          FROM v_case_bundle e
          WHERE case_name=? ORDER BY e.priority DESC, e.ts_utc ASC;
        """, (cname,)).fetchall()
    lines = []
    lines.append(f"# Case: {cname}")
    if cnote: lines.append(f"\n> {cnote}")
    lines.append(f"\n_Created: {ccreated}_\n")
    for r in rows:
        eid, url, page, title, quote, tags, status, prio, t0, t1, ts, sha = r
        tclip = ""
        if (t0 is not None) or (t1 is not None):
            tclip = f" (t={t0 or 0:.2f}–{t1 or 0:.2f}s)"
        lines.append(f"---\n**Evidence #{eid}** — **{title or '(untitled)'}**\n")
        if page and page > 0:
            lines.append(f"- Citation: p.{page} — {url}")
        else:
            lines.append(f"- Link: {url}{tclip}")
        if sha:
            lines.append(f"- Doc hash: `{sha}`")
        lines.append(f"- Status: `{status}`  •  Priority: `{prio}`  •  Tags: `{tags or ''}`")
        lines.append(f"- Added: {ts}\n")
        if quote:
            lines.append("> " + quote.replace("\n", " ").strip())
        lines.append("")  # spacer
    text = "\n".join(lines).strip() + "\n"
    if not outfile:
        outdir = os.path.join(ROOT, "exports"); os.makedirs(outdir, exist_ok=True)
        safe = cname.replace(" ", "_")
        outfile = os.path.join(outdir, f"{safe}.md")
    open(outfile, "w", encoding="utf-8").write(text)
    return {"ok": True, "export": outfile, "count": len(rows)}

def main():
    ensure_views()
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)

    p_new = sp.add_parser("new", help="create a case")
    p_new.add_argument("name"); p_new.add_argument("--note", default="")

    p_ls  = sp.add_parser("ls", help="list cases")

    p_add = sp.add_parser("add", help="attach evidence to case")
    p_add.add_argument("case"); p_add.add_argument("evidence_id", nargs="+")

    p_rm  = sp.add_parser("rm", help="detach evidence from case")
    p_rm.add_argument("case"); p_rm.add_argument("evidence_id", nargs="+")

    p_show= sp.add_parser("show", help="show case bundle")
    p_show.add_argument("case"); p_show.add_argument("--limit", type=int, default=50)

    p_exp = sp.add_parser("export", help="export case to Markdown")
    p_exp.add_argument("case"); p_exp.add_argument("--out")

    args = ap.parse_args()
    if args.cmd == "new":
        print(json.dumps(new_case(args.name, args.note), ensure_ascii=False))
    elif args.cmd == "ls":
        print(json.dumps(list_cases(), ensure_ascii=False))
    elif args.cmd == "add":
        print(json.dumps(attach(args.case, args.evidence_id), ensure_ascii=False))
    elif args.cmd == "rm":
        print(json.dumps(detach(args.case, args.evidence_id), ensure_ascii=False))
    elif args.cmd == "show":
        print(json.dumps(show_case(args.case, args.limit), ensure_ascii=False))
    elif args.cmd == "export":
        print(json.dumps(export_md(args.case, args.out), ensure_ascii=False))

if __name__ == "__main__":
    main()
