#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, os, json
DB="/storage/emulated/0/Download/TornadoAI/corpus.db"

def has_col(c, table, col):
    return any(r[1]==col for r in c.execute(f"PRAGMA table_info({table})"))

def main():
    actions=[]
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA busy_timeout=6000;")
        # Add new columns if missing
        if not has_col(c, "evidence", "propaganda_score"):
            c.execute("ALTER TABLE evidence ADD COLUMN propaganda_score REAL DEFAULT 0.0")
            actions.append("added:evidence.propaganda_score")
        if not has_col(c, "evidence", "propaganda_tags"):
            c.execute("ALTER TABLE evidence ADD COLUMN propaganda_tags TEXT DEFAULT ''")
            actions.append("added:evidence.propaganda_tags")
    print(json.dumps({"ok":True,"actions":actions}))
if __name__=="__main__": main()
