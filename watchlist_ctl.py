#!/data/data/com.termux/files/usr/bin/python3
import csv, sys, argparse, os

ROOT = "/storage/emulated/0/Download/TornadoAI"
WATCH = os.path.join(ROOT, "watchlist.csv")
FIELDS = ["tag","query","urlfilter","case_name","priority"]

def _read():
    rows=[]
    if os.path.exists(WATCH):
        with open(WATCH, "r", encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            for r in rd:
                rows.append({
                    "tag": (r.get("tag") or "").strip(),
                    "query": (r.get("query") or "").strip(),
                    "urlfilter": (r.get("urlfilter") or "%").strip() or "%",
                    "case_name": (r.get("case_name") or (r.get("tag") or "")).strip(),
                    "priority": int((r.get("priority") or "0").strip() or 0),
                })
    return rows

def _write(rows):
    os.makedirs(ROOT, exist_ok=True)
    with open(WATCH, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)

def cmd_list(_):
    rows=_read()
    if not rows:
        print("(empty)")
        return
    # pretty print
    for r in rows:
        print(f"{r['tag']:<16} {r['priority']:<2}  {r['case_name']:<24} {r['urlfilter']:<26} {r['query']}")

def cmd_add(a):
    rows=_read()
    urlfilter = (a.urlfilter or "%").strip() or "%"
    case_name = (a.case or a.tag).strip()
    # upsert by tag
    found=False
    for r in rows:
        if r["tag"] == a.tag:
            r.update({
                "query": a.query.strip(),
                "urlfilter": urlfilter,
                "case_name": case_name,
                "priority": int(a.priority or 0),
            })
            found=True
            break
    if not found:
        rows.append({
            "tag": a.tag.strip(),
            "query": a.query.strip(),
            "urlfilter": urlfilter,
            "case_name": case_name,
            "priority": int(a.priority or 0),
        })
    _write(rows)
    print("[ok] added")

def cmd_remove(a):
    rows=_read()
    before=len(rows)
    rows=[r for r in rows if r["tag"] != a.tag]
    _write(rows)
    print("[ok] removed" if len(rows)<before else "[noop] not found")

def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)

    ap_add = sp.add_parser("add")
    ap_add.add_argument("--tag", required=True)
    ap_add.add_argument("--query", required=True)
    ap_add.add_argument("--urlfilter", required=False, default="%")
    ap_add.add_argument("--case", required=False, default=None)
    ap_add.add_argument("--priority", required=False, type=int, default=0)
    ap_add.set_defaults(func=cmd_add)

    ap_rm = sp.add_parser("remove")
    ap_rm.add_argument("--tag", required=True)
    ap_rm.set_defaults(func=cmd_remove)

    ap_ls = sp.add_parser("list")
    ap_ls.set_defaults(func=cmd_list)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
