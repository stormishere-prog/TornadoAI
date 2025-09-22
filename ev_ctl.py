#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, argparse, json, time, sys

DB="corpus.db"

def _get(c, evid):
    r=c.execute("""
      SELECT e.id, e.url, e.page_no, e.quote, e.note, e.tags, e.status, e.priority,
             e.ts_utc, IFNULL(d.title,'') AS title
      FROM evidence e LEFT JOIN docs d ON d.url=e.url
      WHERE e.id=?""",(evid,)).fetchone()
    return r

def _parse_tags(s):
    return ",".join(sorted(set(t.strip() for t in s.split(",") if t.strip())))

def cmd_list(args):
    q = """SELECT e.id, IFNULL(d.title,''), e.url, e.page_no, e.status, e.priority,
                  substr(e.quote,1,120) AS snip, IFNULL(e.tags,'') AS tags,
                  datetime(e.ts_utc,'unixepoch') AS added
           FROM evidence e
           LEFT JOIN docs d ON d.url=e.url"""
    p = []
    if args.case:
        q += """ JOIN case_evidence ce ON ce.evidence_id=e.id
                 JOIN cases c ON c.id=ce.case_id
                 WHERE c.name=?"""
        p.append(args.case)
    q += " ORDER BY e.id DESC LIMIT ?"
    p.append(args.limit)
    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        rows=c.execute(q, p).fetchall()
    for r in rows:
        print(f"#{r['id']} [{r['status']}/p{r['priority']}] {r['title'][:80]}")
        print(f"  p.{r['page_no']}  {r['url']}")
        if r['tags']: print(f"  tags: {r['tags']}")
        print(f"  {r['snip']}")
        print(f"  added: {r['added']}")
        print("-")

def cmd_show(args):
    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        r=_get(c, args.id)
        if not r: print("not found"); return
        print(json.dumps({k:r[k] for k in r.keys()}, ensure_ascii=False, indent=2))

def cmd_set(args):
    fields=[]
    params=[]
    if args.status: fields.append("status=?"); params.append(args.status)
    if args.priority is not None: fields.append("priority=?"); params.append(args.priority)
    if not fields: print("nothing to update"); return
    params.append(args.id)
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute(f"UPDATE evidence SET {', '.join(fields)} WHERE id=?", params)
    print("[ok] updated")

def cmd_tag(args):
    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        r=_get(c, args.id)
        if not r: print("not found"); return
        existing=_parse_tags((r["tags"] or ""))
        to_add=_parse_tags(args.tags)
        new=set(existing.split(",")) if existing else set()
        new |= set(to_add.split(",")) if to_add else set()
        new_str=",".join(sorted(t for t in new if t))
        c.execute("UPDATE evidence SET tags=? WHERE id=?", (new_str, args.id))
    print(f"[ok] tags -> {new_str or '(none)'}")

def cmd_untag(args):
    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        r=_get(c, args.id)
        if not r: print("not found"); return
        existing=set((r["tags"] or "").split(",")) if r["tags"] else set()
        for t in args.tags.split(","):
            existing.discard(t.strip())
        new_str=",".join(sorted(t for t in existing if t))
        c.execute("UPDATE evidence SET tags=? WHERE id=?", (new_str, args.id))
    print(f"[ok] tags -> {new_str or '(none)'}")

def cmd_note(args):
    with sqlite3.connect(DB, timeout=30) as c:
        c.row_factory=sqlite3.Row
        r=_get(c, args.id)
        if not r: print("not found"); return
        if args.mode=="append" and r["note"]:
            new = r["note"].rstrip() + "\n" + args.text
        else:
            new = args.text
        c.execute("UPDATE evidence SET note=? WHERE id=?", (new, args.id))
    print("[ok] note updated")

def main():
    ap=argparse.ArgumentParser(description="Evidence control (list/show/tag/status/priority/note)")
    sub=ap.add_subparsers(dest="cmd", required=True)

    a=sub.add_parser("list"); a.add_argument("--case", default=""); a.add_argument("--limit", type=int, default=20); a.set_defaults(fn=cmd_list)
    s=sub.add_parser("show"); s.add_argument("--id", type=int, required=True); s.set_defaults(fn=cmd_show)
    u=sub.add_parser("set");  u.add_argument("--id", type=int, required=True); u.add_argument("--status", choices=["open","triaged","dismissed","escalated","reported"]); u.add_argument("--priority", type=int); u.set_defaults(fn=cmd_set)
    t=sub.add_parser("tag");  t.add_argument("--id", type=int, required=True); t.add_argument("--tags", required=True, help="comma separated"); t.set_defaults(fn=cmd_tag)
    g=sub.add_parser("untag");g.add_argument("--id", type=int, required=True); g.add_argument("--tags", required=True); g.set_defaults(fn=cmd_untag)
    n=sub.add_parser("note"); n.add_argument("--id", type=int, required=True); n.add_argument("--mode", choices=["set","append"], default="append"); n.add_argument("--text", required=True); n.set_defaults(fn=cmd_note)

    args=ap.parse_args(); args.fn(args)

if __name__=="__main__": main()
