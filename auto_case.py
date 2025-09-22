#!/data/data/com.termux/files/usr/bin/python3
# Auto-case helper: guess a case from evidence context and link it

import re, os, time, json, sqlite3

DB = "corpus.db"

# ---------- small retrying connector ----------
def _conn(db_path=DB):
    delay=0.2
    for _ in range(8):
        try:
            c = sqlite3.connect(db_path, timeout=30)
            c.execute("PRAGMA busy_timeout=6000;")
            return c
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                import time as _t; _t.sleep(delay); delay=min(delay*1.8, 3.0); continue
            raise
    return sqlite3.connect(db_path, timeout=30)

# ---------- keyword → case rules ----------
CASE_KEYWORDS = [
    (r"\bmk[\s\-]?ultra\b",                  "MKULTRA"),
    (r"\boperation\s+mockingbird\b",        "Operation-Mockingbird"),
    (r"\bchurch\s+committee\b",              "Church-Committee"),
    (r"\bcointel\s*pro\b",                   "COINTELPRO"),
    (r"\b(fisa|section)\s*702\b",            "FISA-702"),
    (r"\bunmasking\b",                       "Unmasking"),
    (r"\bnsa\s+bulk\s+collection\b",         "NSA-Bulk-Collection"),
    (r"\bforeign\s+intelligence\b",          "Foreign-Intelligence"),
    (r"\bclassified\s+information\s+procedures\s+act\b", "CIPA"),
]

DOMAIN_HINTS = [
    (r"^https?://vault\.fbi\.gov/",          "FBI-Vault"),
    (r"^https?://www\.cia\.gov/readingroom", "CIA-Reading-Room"),
    (r"^https?://www\.dni\.gov/",            "DNI"),
    (r"^https?://www\.nsa\.gov/.*foia",      "NSA-FOIA"),
    (r"^https?://www\.justice\.gov/oip",     "DOJ-OIP"),
    (r"^https?://aad\.archives\.gov/",       "NARA-AAD"),
    (r"^https?://www\.whitehouse\.gov/",     "White-House"),
]

def _norm(s): return (s or "").strip().lower()

def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "Misc"

def guess_case(url:str, title:str, snippet:str, from_search:str=""):
    text = " ".join([_norm(url), _norm(title), _norm(snippet), _norm(from_search)])

    # 1) explicit keyword hits
    for pat, case in CASE_KEYWORDS:
        if re.search(pat, text, re.I):
            return case

    # 2) domain hints (stable buckets)
    for pat, case in DOMAIN_HINTS:
        if re.search(pat, url or "", re.I):
            return case

    # 3) derive a reasonable bucket from filenames like ".../bash_unmasking_report_05_31_22"
    m = re.search(r"/([A-Za-z0-9._-]{8,})\.pdf\b", url or "")
    if m:
        stem = re.sub(r"\.pdf$", "", m.group(1), flags=re.I)
        # keep only letters/digits & dashes
        stem = _slugify(stem)
        if stem:
            return stem

    # 4) default
    return "General-FOIA"

def ensure_case(c, name:str, note:str=""):
    c.execute("INSERT OR IGNORE INTO cases(name, note, created_utc) VALUES(?,?, strftime('%s','now'))",
              (name, note or ""))
    row = c.execute("SELECT id FROM cases WHERE name=?", (name,)).fetchone()
    return row[0]

def link_case_evidence(c, case_name:str, evidence_id:int):
    case_id = ensure_case(c, case_name)
    c.execute("INSERT OR IGNORE INTO case_evidence(case_id, evidence_id, added_utc) VALUES(?,?, strftime('%s','now'))",
              (case_id, evidence_id))

def auto_case_for_evidence(url:str, title:str, snippet:str, from_search:str=""):
    return guess_case(url, title, snippet, from_search)

if __name__ == "__main__":
    # tiny self-test
    tests = [
        ("https://vault.fbi.gov/recently-added", "COINTELPRO doc", "COINTELPRO program", ""),
        ("https://www.cia.gov/readingroom/...", "MKULTRA memo", "behavioral...", ""),
        ("https://www.justice.gov/oip/.../bash_unmasking_report_05_31_22/download", "", "Section 702 minimization", ""),
    ]
    out=[]
    for u,t,s,q in tests:
        out.append({"url":u,"case":guess_case(u,t,s,q)})
    print(json.dumps({"ok":True,"samples":out}))
