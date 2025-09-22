#!/data/data/com.termux/files/usr/bin/python3
import os, sys, csv, json, time, sqlite3, subprocess, shlex, pathlib

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")
WL   = os.path.join(ROOT, "watchlist.tsv")
ALERT_DIR = os.path.join(ROOT, "alerts")
os.makedirs(ALERT_DIR, exist_ok=True)

def _run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def _read_watchlist():
    if not os.path.exists(WL):
        return []
    rows = []
    with open(WL, "r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            rows.append({
                "tag": r.get("tag","").strip(),
                "query": r.get("query","").strip(),
                "urlfilter": r.get("urlfilter","").strip() or "%",
                "case": r.get("case","").strip() or "General",
                "priority": int(r.get("priority","1") or 1),
            })
    return rows

def _evidence_exists(c, url, page):
    row = c.execute("SELECT 1 FROM evidence WHERE url=? AND page_no=?", (url, page)).fetchone()
    return bool(row)

def main():
    # Schema safety (via your guard)
    # (safe_run.sh will have called evidence_migrate already)

    wl = _read_watchlist()
    if not wl:
        print(json.dumps({"ok": True, "hits": 0, "note": "watchlist empty"}))
        return

    ts = time.strftime("%Y%m%d-%H%M%S")
    report_path = os.path.join(ALERT_DIR, f"alert-{ts}.txt")
    digest = []

    hits_total = 0
    new_evd = 0

    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        for item in wl:
            tag = item["tag"]; query=item["query"]; urlf=item["urlfilter"]; case=item["case"]; prio=item["priority"]

            # search (top few concise hits)
            cmd = [
                "python3", "search_pages.py", query,
                "--urlfilter", urlf, "--limit", "5"
            ]
            rc, out, err = _run(cmd)
            if rc != 0 or not out.strip():
                continue

            try:
                data = json.loads(out)
            except Exception:
                continue

            found = 0
            for h in data.get("hits", []):
                url = h.get("url"); page = h.get("page"); snip = (h.get("snippet") or "").replace("\n"," ").strip()
                if not url or not page:
                    continue
                found += 1; hits_total += 1

                # skip if we already have this page cited
                if _evidence_exists(c, url, page):
                    digest.append(f"[{tag}] (dup) p.{page} {url}\n  {snip[:160]}")
                    continue

                # mark evidence and auto-link case
                # 1) insert evidence
                c.execute("""INSERT INTO evidence(url,page_no,quote,note,ts_utc,priority)
                             VALUES(?,?,?,?,strftime('%s','now'),?)""",
                          (url, int(page), snip[:800], f"watch:{tag}", prio))
                eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]

                # 2) ensure case exists
                c.execute("INSERT OR IGNORE INTO cases(name) VALUES(?)", (case,))
                cid = c.execute("SELECT id FROM cases WHERE name=?", (case,)).fetchone()[0]

                # 3) link
                c.execute("""INSERT OR IGNORE INTO case_evidence(case_id, evidence_id)
                             VALUES(?,?)""", (cid, eid))

                new_evd += 1
                digest.append(f"[{tag}] (+NEW) case={case} prio={prio} p.{page} {url}\n  {snip[:160]}")

            if found == 0:
                digest.append(f"[{tag}] (no hits) query={query} filter={urlf}")

    # write report (simple text for now)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Watchlist run @ {ts}\n")
        f.write(f"Total hits: {hits_total} | New evidence: {new_evd}\n\n")
        for line in digest:
            f.write(line+"\n")

    # also drop a small JSON summary
    json_path = os.path.join(ALERT_DIR, "last_alert.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"ts": ts, "hits": hits_total, "new": new_evd, "report": report_path}, jf, ensure_ascii=False)

    print(json.dumps({"ok": True, "hits": hits_total, "new": new_evd, "report": report_path}))
