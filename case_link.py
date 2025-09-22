#!/data/data/com.termux/files/usr/bin/python3
import argparse, sqlite3, time, json, sys, os

ROOT = os.path.dirname(__file__) or "."
DB = os.path.join(ROOT, "corpus.db")

def ensure_case(c, name):
    c.execute("INSERT OR IGNORE INTO cases(name, note, created_utc) VALUES(?,?,?)",
              (name, "", int(time.time())))
    row = c.execute("SELECT id FROM cases WHERE name=?", (name,)).fetchone()
    return row[0]

def link_evidence_to_case(c, case_name, evidence_id):
    cid = ensure_case(c, case_name)
    c.execute("INSERT OR IGNORE INTO case_evidence(case_id, evidence_id, added_utc) VALUES(?,?,?)",
              (cid, evidence_id, int(time.time())))
    return cid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--evidence-id", type=int, required=True)
    args = ap.parse_args()

    with sqlite3.connect(DB, timeout=30) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        cid = link_evidence_to_case(conn, args.case, args.evidence_id)
    print(json.dumps({"ok": True, "case_id": cid}))
if __name__ == "__main__":
    main()
