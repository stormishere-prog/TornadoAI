#!/data/data/com.termux/files/usr/bin/python3
import os, re, sqlite3, time, math, urllib.parse

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT,"corpus.db")

KW_LOADED_LANGUAGE = [
  # boosters / vilifiers commonly found in persuasive gov/media prose
  r"\bunprecedented\b", r"\bgrave\b", r"\bsevere\b", r"\bextraordinary\b",
  r"\bexistential\b", r"\bcatastroph(ic|e)\b", r"\bunpatriotic\b",
  r"\benemies of (the )?state\b", r"\bdefinitive\b", r"\bbeyond doubt\b",
  r"\bclear(ly)? and present danger\b", r"\bdisinformation\b", r"\bmisinformation\b",
  r"\bextremist\b", r"\bterror(ist|ism)\b", r"\bforeign adversar(y|ies)\b"
]
KW_APPEALS_AUTHORITY = [
  r"\bas (?:ordered|directed) by (?:the )?President\b",
  r"\bby (?:the )?authority vested in me\b",
  r"\bper (?:EO|Executive Order) \d+\b", r"\bFISC[- ]approved\b",
  r"\bpursuant to (?:Section|§)\s?\d+", r"\bunder Title \d+\b"
]
KW_BANDWAGON_OR_NEEDLESS_UNITY = [
  r"\bwe (?:must|shall|will) all\b", r"\bnational consensus\b", r"\bunited we\b",
]
KW_DISSENT_DISMISSAL = [
  r"\bconspiracy theor(y|ies)\b", r"\bunfounded\b", r"\bdebunked\b", r"\bfringe\b"
]
KW_FEAR_APPEALS = [
  r"\bimminent (?:threat|danger)\b", r"\burgent\b", r"\bemergency\b"
]

def compile_any(patterns): 
    return re.compile("|".join(patterns), re.I)

RE_LOADED = compile_any(KW_LOADED_LANGUAGE)
RE_AUTH   = compile_any(KW_APPEALS_AUTHORITY)
RE_BAND   = compile_any(KW_BANDWAGON_OR_NEEDLESS_UNITY)
RE_DIS    = compile_any(KW_DISSENT_DISMISSAL)
RE_FEAR   = compile_any(KW_FEAR_APPEALS)

# Simple source weighting: official.gov domains tend to use “formal justification” rhetoric
def source_weight(url:str)->float:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.endswith(".gov"): return 1.10
    if host.endswith(".mil"): return 1.10
    if "whitehouse.gov" in host: return 1.15
    if "dni.gov" in host or "justice.gov" in host: return 1.12
    return 1.00

def page_score(txt:str, url:str)->tuple[float,str,str]:
    # base from cues
    n = len(txt)
    if n==0: 
        return (0.0, "neutral", "empty page")

    hits = []
    s = 0.0
    for name, rex, w in [
        ("loaded", RE_LOADED, 0.25),
        ("authority", RE_AUTH, 0.22),
        ("bandwagon", RE_BAND, 0.18),
        ("dismissal", RE_DIS, 0.20),
        ("fear", RE_FEAR, 0.22),
    ]:
        m = rex.findall(txt)
        if m:
            hits.append(f"{name}:{len(m)}")
            s += w * min(len(m), 4)  # cap each cue contribution

    # normalize by length a bit (short blurbs shouldn’t spike too high)
    length_mod = 1.0
    if n < 400: length_mod = 0.85
    elif n > 4000: length_mod = 0.95

    s = s * length_mod * source_weight(url)
    s = max(0.0, min(1.0, s))  # clamp

    if s >= 0.75: label = "High"
    elif s >= 0.55: label = "Medium"
    elif s >= 0.35: label = "Low"
    else: label = "Neutral"

    notes = "; ".join(hits) if hits else "no cues"
    return (s, label, notes)

def ensure_cols(c):
    info = {r[1] for r in c.execute("PRAGMA table_info(doc_pages);")}
    alters=[]
    if "propaganda_score" not in info:
        c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_score REAL;")
        alters.append("add:propaganda_score")
    if "propaganda_label" not in info:
        c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_label TEXT;")
        alters.append("add:propaganda_label")
    if "propaganda_notes" not in info:
        c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_notes TEXT;")
        alters.append("add:propaganda_notes")
    return alters

def main():
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        c.execute("PRAGMA foreign_keys=ON;")
        alters = ensure_cols(c)

        # Only score missing rows or those older than 30 days since scoring note is empty
        rows = c.execute("""
          SELECT p.rowid, p.url, p.page_no, IFNULL(p.text,'')
          FROM doc_pages p
          WHERE p.propaganda_score IS NULL OR p.propaganda_label IS NULL
          LIMIT 5000
        """).fetchall()

        updated=0
        for rowid, url, page, text in rows:
            s, label, notes = page_score(text, url)
            c.execute("""
              UPDATE doc_pages
                 SET propaganda_score=?, propaganda_label=?, propaganda_notes=?
               WHERE rowid=?""", (s, label, notes, rowid))
            updated += 1

        print({"ok": True, "alters": alters, "scored": updated})

if __name__=="__main__":
    main()
