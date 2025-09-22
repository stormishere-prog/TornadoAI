#!/data/data/com.termux/files/usr/bin/python3
# Lightweight propaganda detector for doc_pages → updates score/tags and logs hits
import os, re, time, json, sqlite3, argparse

ROOT = "/storage/emulated/0/Download/TornadoAI"
DB   = os.path.join(ROOT, "corpus.db")

PATTERNS = [
  # bucket, tag, regex, weight
  ("emotional","fear",       r"\b(existential|grave|catastrophic|deadly|dire|devastating)\b", 0.25),
  ("emotional","urgency",    r"\b(unprecedented|immediate action|swift(ly)?|act now|at once)\b", 0.20),
  ("authority","experts",    r"\b(experts? (agree|say|warn)|officials said|authorities confirm)\b", 0.18),
  ("authority","office",     r"\b(by the authority vested in me|by order of|official decree)\b", 0.12),
  ("slogan","slogan",        r"\b(build back better|historic investment|whole-of-government)\b", 0.18),
  ("dismissal","baseless",   r"\b(without evidence|debunked claim|conspiracy theory)\b", 0.15),
  ("bandwagon","consensus",  r"\b(broad consensus|everyone knows|overwhelming support)\b", 0.12),
  ("smears","label",         r"\b(extremist|denier|traitor|unpatriotic)\b", 0.15),
]

def _conn():
  c = sqlite3.connect(DB, timeout=30)
  c.execute("PRAGMA busy_timeout=6000;")
  return c

def _iter_candidates(c, since_days, limit):
  if since_days>0:
    cutoff = int(time.time()) - since_days*86400
    q = """SELECT p.id,p.url,p.page_no,IFNULL(p.text,'') AS text
           FROM doc_pages p JOIN docs d ON d.url=p.url
           WHERE (p.propaganda_score IS NULL OR p.propaganda_score=0.0)
             AND d.ts_utc >= ?
           LIMIT ?"""
    for r in c.execute(q,(cutoff,limit)):
      yield r
  else:
    q = """SELECT id,url,page_no,IFNULL(text,'') FROM doc_pages
           WHERE propaganda_score IS NULL OR propaganda_score=0.0
           LIMIT ?"""
    for r in c.execute(q,(limit,)):
      yield r

def analyze(text):
  hits=[]; tags=set(); score=0.0
  lower=text.lower()
  for bucket, tag, rx, w in PATTERNS:
    for m in re.finditer(rx, lower, flags=re.I):
      s,e = m.start(), m.end()
      snippet = text[max(0,s-80):min(len(text),e+80)]
      hits.append((bucket,tag, w, s,e, snippet))
      tags.add(tag)
      score += w
  # squish score to [0,1] with a soft cap
  score = min(1.0, score)
  return score, sorted(tags), hits

def write_hits(c, url, page_no, hits):
  c.executemany(
    "INSERT INTO propaganda_hits(url,page_no,bucket,tag,conf,start_char,end_char,snippet) VALUES(?,?,?,?,?,?,?,?)",
    [(url,page_no,b,t,w,s,e,snip) for (b,t,w,s,e,snip) in hits]
  )

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--since-days", type=int, default=30, help="only pages from docs newer than N days")
  ap.add_argument("--limit", type=int, default=2000, help="max pages to scan per run")
  args = ap.parse_args()

  done=0; updated=0; logged=0
  with _conn() as c:
    for pid,url,page_no,text in _iter_candidates(c, args.since_days, args.limit):
      done+=1
      score,tags,hits = analyze(text)
      if hits:
        write_hits(c, url, page_no, hits); logged += len(hits)
      c.execute("UPDATE doc_pages SET propaganda_score=?, propaganda_tags=? WHERE id=?",
                (float(score), ",".join(tags), pid))
      updated+=1
  print(json.dumps({"ok":True,"scanned":done,"updated":updated,"hits_logged":logged}))
if __name__=="__main__": main()
