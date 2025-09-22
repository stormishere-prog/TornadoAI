#!/data/data/com.termux/files/usr/bin/python3
import os, re, sqlite3, subprocess, tempfile, time, sys

ROOT = os.getcwd()
PDF_DIR = os.path.join(ROOT, "pdfs")
DB = os.path.join(ROOT, "corpus.db")

os.makedirs(PDF_DIR, exist_ok=True)

def run(cmd, timeout=60):
    try:
        subprocess.run(cmd, check=True, timeout=timeout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def read_text(p, max_chars=4000):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:max_chars]
    except Exception:
        return ""

def sanitize(s):
    s = re.sub(r"\s{2,}", " ", s or "")
    return s.strip()

def extract_text_from_pdf(path):
    base = os.path.splitext(os.path.basename(path))[0]
    tmpdir = tempfile.mkdtemp(prefix="pdf_")
    txtfile = os.path.join(tmpdir, base + ".txt")

    # 1) Try embedded text first
    if run(["pdftotext", "-enc", "UTF-8", path, txtfile], timeout=40):
        txt = read_text(txtfile)
        if len(txt.strip()) >= 50:
            return sanitize(txt)

    # 2) OCR fallback: render pages then tesseract
    #    (200dpi is a decent balance of accuracy/speed for phones)
    ok_ppm = run(["pdftoppm", "-r", "200", "-png", path, os.path.join(tmpdir, "page")], timeout=120)
    if ok_ppm:
        ocr_txt = []
        for fname in sorted(os.listdir(tmpdir)):
            if not fname.lower().endswith(".png"): continue
            img = os.path.join(tmpdir, fname)
            outbase = os.path.join(tmpdir, fname.rsplit(".",1)[0])
            if run(["tesseract", img, outbase, "--psm", "3"], timeout=60):
                part = read_text(outbase + ".txt")
                if part: ocr_txt.append(part)
        full = sanitize(" ".join(ocr_txt))
        if len(full) >= 50:
            return full

    return ""

def title_from_text(text, fallback):
    # crude first-line as title, sanitized
    line = (text.splitlines() or [""])[0]
    line = sanitize(line)
    if len(line) >= 8:
        return line[:160]
    return fallback

def upsert_doc(c, url, title, content, trust=50):
    c.execute("""
      INSERT OR REPLACE INTO docs(url, title, content, ts_utc, source_trust, sha256)
      VALUES(?,?,?,?,?,?)
    """, (url, title, content, int(time.time()), trust, ""))

def main():
    if not os.path.exists(DB):
        print('{"error":"corpus.db not found. Run the DB init first."}')
        sys.exit(1)

    added = 0
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("BEGIN IMMEDIATE;")
        try:
            for entry in sorted(os.listdir(PDF_DIR)):
                if not entry.lower().endswith(".pdf"): continue
                path = os.path.join(PDF_DIR, entry)
                text = extract_text_from_pdf(path)
                if not text:
                    # skip silently if unreadable
                    continue
                url = "file://" + path
                title = title_from_text(text, os.path.basename(path))
                upsert_doc(conn, url, title, text, trust=60)
                added += 1
            conn.execute("COMMIT;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            print('{"error":"ingest_failed: %s"}' % str(e))
            sys.exit(2)

    print('{"ok": true, "added": %d}' % added)

if __name__ == "__main__":
    main()
