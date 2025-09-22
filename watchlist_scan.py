#!/data/data/com.termux/files/usr/bin/python3
import csv, json, argparse, subprocess, time, os
from pathlib import Path

ROOT = Path("/storage/emulated/0/Download/TornadoAI")
WATCH = ROOT/"watchlist.csv"

def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def _search(query, urlfilter, limit):
    # use the existing CLI to stay consistent
    cmd = ["python3", "search_pages.py", query, "--limit", str(limit)]
    if urlfilter:
        cmd += ["--urlfilter", urlfilter]
    rc,out,err = _run(cmd)
    if rc != 0:
        return {"hits":[]}
    try:
        return json.loads(out)
    except Exception:
        return {"hits":[]}

def _auto_case_mark(url, page, snippet, tag, q, case_name=None, priority=0):
    note = f"watch:{tag} | query:{q}"
    args = [
        "python3","auto_case_mark.py",
        "--url", url,
        "--page", str(page),
        "--quote", snippet.replace('"',''),
        "--note", note,
        "--from-search", q
    ]
    if case_name:
        args += ["--case", case_name]
    if priority:
        args += ["--priority", str(priority)]
    return _run(args)

def _append_alerts(log_path, jsonl_path, rec):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec["ts"]))
    line = (f"[{ts}] tag={rec['tag']} case={rec['case']} prio={rec['priority']} "
            f"url={rec['url']} p={rec['page']} :: {rec['snippet'][:140]}")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-tag", type=int, default=1)
    ap.add_argument("--alerts", default="alerts")  # basename for alerts.{log,jsonl}
    args = ap.parse_args()

    log_path  = ROOT/(args.alerts + ".log")
    json_path = ROOT/(args.alerts + ".jsonl")

    added = []
    if not WATCH.exists():
        print(json.dumps({"ok":True,"added":[]}))
        return

    with WATCH.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        tag       = (row.get("tag") or "").strip()
        q         = (row.get("query") or "").strip()
        urlfilter = (row.get("urlfilter") or "").strip()
        case_name = (row.get("case_name") or "").strip() or tag
        prio      = int(row.get("priority") or 0)

        if not tag or not q:
            continue

        res = _search(q, urlfilter, args.max_per_tag)
        hits = res.get("hits", [])[:args.max_per_tag] if res.get("hits") else res.get("hits", [])
        count = 0
        for h in hits:
            url = h.get("url"); page = h.get("page"); snippet = (h.get("snippet") or "")[:500]
            if not url or not page:
                continue
            # Commit evidence + case link
            rc,out,err = _auto_case_mark(url, page, snippet, tag, q, case_name=case_name, priority=prio)
            if rc == 0:
                rec = {
                    "ts": int(time.time()),
                    "tag": tag,
                    "case": case_name,
                    "priority": prio,
                    "url": url,
                    "page": page,
                    "query": q,
                    "snippet": snippet
                }
                _append_alerts(log_path, json_path, rec)
                added.append(rec)
                count += 1
            if count >= args.max_per_tag:
                break

    print(json.dumps({"ok":True, "added": added}, ensure_ascii=False))

if __name__ == "__main__":
    main()
