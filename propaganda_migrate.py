#!/data/data/com.termux/files/usr/bin/python3
import os, sqlite3, time

ROOT="/storage/emulated/0/Download/TornadoAI"
DB=os.path.join(ROOT, "corpus.db")

def has_col(c, table, col):
    return any(r[1] == col for r in c.execute(f"PRAGMA table_info({table});"))

def ensure():
    actions=[]
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        c.execute("PRAGMA foreign_keys=ON;")
        # Add columns if missing
        if not has_col(c, "doc_pages", "propaganda_score"):
            c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_score REAL;")
            actions.append("add:doc_pages.propaganda_score")
        if not has_col(c, "doc_pages", "propaganda_label"):
            c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_label TEXT;")
            actions.append("add:doc_pages.propaganda_label")
        if not has_col(c, "doc_pages", "propaganda_notes"):
            c.execute("ALTER TABLE doc_pages ADD COLUMN propaganda_notes TEXT;")
            actions.append("add:doc_pages.propaganda_notes")
        # Convenience view for reporting
        c.executescript("""
        CREATE VIEW IF NOT EXISTS v_propaganda_pages AS
        SELECT p.url, p.page_no, p.text,
               p.propaganda_score, p.propaganda_label, p.propaganda_notes,
               d.title, d.ts_utc
        FROM doc_pages p
        JOIN docs d ON d.url = p.url;
        """)
    print({"ok": True, "actions": actions})

if __name__=="__main__":
    ensure()
