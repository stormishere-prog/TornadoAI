#!/data/data/com.termux/files/usr/bin/python3
import os, csv, sqlite3, argparse, json, time

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")
OUTDIR=os.path.join(ROOT,"exports")

def conn():
    c=sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA foreign_keys=ON;")
    return c

def get_case_rows(case_name_or_id):
    with conn() as c:
        ci=c.execute("SELECT id,name,note,datetime(created_utc,'unixepoch') FROM cases WHERE name=? OR id=?",
                     (case_name_or_id, case_name_or_id)).fetchone()
        if not ci: return None, []
        cname, cnote, ccreated = ci[1], ci[2], ci[3]
        rows=c.execute("""
           SELECT e.id, e.url, e.page_no, e.title, e.quote, e.tags, e.status, e.priority,
                  e.t_start, e.t_end, datetime(e.ts_utc,'unixepoch'), e.doc_sha256
           FROM v_case_bundle e
           WHERE case_name=?
           ORDER BY e.priority DESC, e.ts_utc ASC;
        """,(cname,)).fetchall()
    meta={"name":cname,"note":cnote or "","created":ccreated}
    return meta, rows

def export_md(meta, rows, path_md):
    lines=[]
    lines.append(f"# Case: {meta['name']}")
    if meta["note"]:
        lines.append(f"\n> {meta['note']}")
    lines.append(f"\n_Created: {meta['created']}_\n")
    for r in rows:
        eid,url,page,title,quote,tags,status,prio,t0,t1,ts,sha=r
        tclip=""
        if (t0 is not None) or (t1 is not None):
            tclip=f" (t={ (t0 or 0):.2f}–{ (t1 or 0):.2f}s)"
        lines.append(f"---\n**Evidence #{eid}** — **{title or '(untitled)'}**\n")
        if page and page>0:
            lines.append(f"- Citation: p.{page} — {url}")
        else:
            lines.append(f"- Link: {url}{tclip}")
        if sha:
            lines.append(f"- Doc hash: `{sha}`")
        lines.append(f"- Status: `{status}`  •  Priority: `{prio}`  •  Tags: `{tags or ''}`")
        lines.append(f"- Added: {ts}\n")
        if quote:
            lines.append("> " + (quote or "").replace("\n"," ").strip())
        lines.append("")
    open(path_md,"w",encoding="utf-8").write("\n".join(lines).strip()+"\n")

def export_csv(meta, rows, path_csv):
    with open(path_csv,"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["case_name", meta["name"]])
        w.writerow(["note", meta["note"]])
        w.writerow(["created", meta["created"]])
        w.writerow([])
        w.writerow(["evidence_id","title","url","page","t_start","t_end","status","priority","tags","doc_sha256","added","quote"])
        for r in rows:
            eid,url,page,title,quote,tags,status,prio,t0,t1,ts,sha=r
            w.writerow([eid, title or "", url, page or "", t0 or "", t1 or "", status or "open",
                        prio or 0, tags or "", sha or "", ts or "", (quote or "").replace("\n"," ")])

def try_export_pdf(meta, rows, path_pdf):
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except Exception:
        return {"ok": False, "hint": "reportlab not installed; wrote MD/CSV."}

    c=canvas.Canvas(path_pdf, pagesize=LETTER)
    w,h=LETTER
    margin=0.75*inch
    x=margin; y=h-margin
    def line(txt, bold=False):
        nonlocal y
        if y<margin+0.5*inch:
            c.showPage(); y=h-margin
        if bold:
            c.setFont("Helvetica-Bold",10)
        else:
            c.setFont("Helvetica",10)
        c.drawString(x, y, txt[:110])
        y-=12

    c.setTitle(f"Case: {meta['name']}")
    line(f"Case: {meta['name']}", bold=True)
    if meta["note"]: line(f"Note: {meta['note']}")
    line(f"Created: {meta['created']}")
    line("-"*80)
    for r in rows:
        eid,url,page,title,quote,tags,status,prio,t0,t1,ts,sha=r
        line(f"Evidence #{eid} — {title or '(untitled)'}", bold=True)
        if page and page>0: line(f"Citation: p.{page} — {url}")
        else:
            seg = f"Link: {url}"
            if (t0 is not None) or (t1 is not None):
                seg += f"  (t={ (t0 or 0):.2f}–{ (t1 or 0):.2f}s)"
            line(seg)
        if sha: line(f"Doc hash: {sha}")
        line(f"Status: {status or 'open'}  •  Priority: {prio or 0}  •  Tags: {tags or ''}")
        line(f"Added: {ts}")
        if quote:
            # wrap simple
            q=("> " + quote.replace("\n"," ").strip())
            while q:
                line(q[:110]); q=q[110:]
        line("-"*80)
    c.save()
    return {"ok": True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--base", help="basename (without extension) for outputs")
    ap.add_argument("--pdf", action="store_true", help="also try to create PDF (needs reportlab)")
    args=ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    meta, rows = get_case_rows(args.case)
    if not meta:
        print(json.dumps({"ok":False,"error":"case not found"})); return

    base = args.base or meta["name"].replace(" ","_")
    path_md = os.path.join(OUTDIR, base + ".md")
    path_csv= os.path.join(OUTDIR, base + ".csv")
    export_md(meta, rows, path_md)
    export_csv(meta, rows, path_csv)

    out={"ok":True,"md":path_md,"csv":path_csv,"count":len(rows)}
    if args.pdf:
        path_pdf=os.path.join(OUTDIR, base + ".pdf")
        ok = try_export_pdf(meta, rows, path_pdf)
        if ok.get("ok"):
            out["pdf"]=path_pdf
        else:
            out["pdf_hint"]=ok.get("hint")
    print(json.dumps(out, ensure_ascii=False))

if __name__=="__main__": main()
