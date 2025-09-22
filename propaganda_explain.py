#!/data/data/com.termux/files/usr/bin/python3
import re, json, sqlite3, argparse, textwrap

DB="corpus.db"

# Very small starter lexicon. You can extend safely.
LEX = {
  "fear_appeal":       [r"\b(grave|serious|existential)\s+threat", r"\bdoom(ed|ing)?\b", r"\bcatastroph(ic|e)\b", r"\bterrori(st|sm)\b"],
  "loaded_language":   [r"\btraitor(s)?\b", r"\benh(a|ä)mie(s)?\b", r"\bbetray(al|ed)\b", r"\bcorrupt(ion)?\b"],
  "scapegoating":      [r"\b(blame|fault)\s+(the|those)\b", r"\bthey\s+are\s*to\s+blame\b"],
  "bandwagon":         [r"\bevery(one|body)\s+knows\b", r"\bthe (people|majority)\b"],
  "whataboutism":      [r"\bwhat\s+about\b", r"\bbut\s+(they|you)\b"],
  "glittering_generalities":[r"\bfreedom\b", r"\bpatriot(ism|ic)\b", r"\bvalues\b"],
  "ad_hominem":        [r"\bidiot(ic)?\b", r"\bmoron(ic)?\b", r"\bcrook(ed)?\b"],
  "appeal_to_authority":[r"\b(as|per)\s+(experts?|authorities?)\b", r"\bclassified sources\b"],
  "card_stacking":     [r"\bonly\b\s+\b(show|present|include)\b", r"\bignore\b\s+\bfacts?\b"],
  "false_dilemma":     [r"\beither\b\s+.*\s+\bor\b\s+.*\b", r"\bno\s+alternative\b"]
}

TAG_LABELS = {
  "fear_appeal": "Fear appeal",
  "loaded_language": "Loaded language",
  "scapegoating": "Scapegoating",
  "bandwagon": "Bandwagon",
  "whataboutism": "Whataboutism",
  "glittering_generalities": "Glittering generalities",
  "ad_hominem": "Ad hominem",
  "appeal_to_authority": "Appeal to authority",
  "card_stacking": "Card stacking",
  "false_dilemma": "False dilemma",
}

def _fetch_page(c, url, page):
    r = c.execute("SELECT text FROM doc_pages WHERE url=? AND page_no=? LIMIT 1", (url, page)).fetchone()
    return r[0] if r else ""

def _coalesce_tags(tags_csv, page_tags_csv):
    # Prefer evidence snapshot tags if present, else page tags
    tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
    if not tags:
        tags = [t.strip() for t in (page_tags_csv or "").split(",") if t.strip()]
    return tags

def _examples(txt, patt, max_hits=2, window=40):
    out=[]
    for m in re.finditer(patt, txt, flags=re.I):
        s=max(0, m.start()-window); e=min(len(txt), m.end()+window)
        snip = txt[s:e].replace("\n"," ").strip()
        out.append(snip)
        if len(out)>=max_hits: break
    return out

def _build_note(url, page, txt, tags):
    hit_lines=[]
    used=0
    for tag in tags:
        key = tag.lower()
        pats = LEX.get(key, [])
        ex_all=[]
        for p in pats:
            ex_all += _examples(txt, p, max_hits=1)
            if len(ex_all) >= 2:
                break
        if ex_all:
            label = TAG_LABELS.get(key, key)
            for ex in ex_all[:2]:
                hit_lines.append(f"{label}: “{ex}”")
                used += 1
                if used >= 4: break
        if used >= 4: break

    if not hit_lines and tags:
        # We have tags but no lexicon hits—fallback generic explanation.
        label_list = ", ".join(TAG_LABELS.get(t,t) for t in tags)
        return f"Flagged for propaganda patterns at save time: {label_list}."

    if not hit_lines:
        return "No specific phrase matches; saved as contextual propaganda snapshot."

    # Compose compact note
    note = "Propaganda cues captured at save time:\n- " + "\n- ".join(hit_lines)
    # Trim to ~400 chars to keep evidence succinct
    return textwrap.shorten(note, width=400, placeholder=" …")

def explain_one(eid):
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        row = c.execute("""
          SELECT e.id, e.url, e.page_no, IFNULL(e.ev_prop_tags,''), e.ev_prop_notes,
                 (SELECT IFNULL(propaganda_tags,'') FROM doc_pages p WHERE p.url=e.url AND p.page_no=e.page_no LIMIT 1)
          FROM evidence e
          WHERE e.id=? LIMIT 1
        """,(eid,)).fetchone()
        if not row:
            return {"ok": False, "error": "evidence not found", "id": eid}
        _, url, page, ev_tags, ev_notes, page_tags = row
        if ev_notes and ev_notes.strip():
            return {"ok": True, "id": eid, "skipped":"already has notes"}

        txt = _fetch_page(c, url, page)
        tags = _coalesce_tags(ev_tags, page_tags)
        note = _build_note(url, page, txt, tags)
        c.execute("UPDATE evidence SET ev_prop_notes=? WHERE id=?", (note, eid))
        return {"ok": True, "id": eid, "updated": True, "note": note}

def explain_bulk():
    updated=0; skipped=0; missing=0
    out=[]
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA foreign_keys=ON;")
        rows = c.execute("""
          SELECT e.id
          FROM evidence e
          WHERE IFNULL(TRIM(e.ev_prop_notes),'')=''
        """).fetchall()
    for (eid,) in rows:
        res = explain_one(eid)
        out.append(res)
        if res.get("updated"): updated+=1
        elif res.get("skipped"): skipped+=1
        else: missing+=1
    return {"ok": True, "updated": updated, "skipped": skipped, "missing": missing}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--id", type=int, help="evidence id to explain")
    ap.add_argument("--bulk", action="store_true", help="fill notes for all evidence that lack notes")
    args=ap.parse_args()
    if args.id:
        print(json.dumps(explain_one(args.id), ensure_ascii=False))
    elif args.bulk:
        print(json.dumps(explain_bulk(), ensure_ascii=False))
    else:
        print(json.dumps({"ok": False, "error": "use --id or --bulk"}))

if __name__=="__main__":
    main()
