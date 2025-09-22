#!/data/data/com.termux/files/usr/bin/python3
import sqlite3, sys, json

DEFAULT_DB = "corpus.db"

DDL = {
  "docs": """
    CREATE TABLE IF NOT EXISTS docs(
      url TEXT PRIMARY KEY,
      title TEXT,
      content TEXT,
      ts_utc INTEGER,
      source_trust INTEGER DEFAULT 0,
      sha256 TEXT
    );
  """,
  "docs_fts": """
    CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
    USING fts5(
      title,
      content,
      url UNINDEXED,
      content='docs',
      content_rowid='rowid'
    );
  """,
  "doc_pages": """
    CREATE TABLE IF NOT EXISTS doc_pages(
      id INTEGER PRIMARY KEY,
      url TEXT REFERENCES docs(url) ON DELETE CASCADE,
      page_no INTEGER,
      text TEXT
    );
  """,
  "pages_fts": """
    CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts
    USING fts5(text, url UNINDEXED, page_no UNINDEXED,
               content='doc_pages', content_rowid='id');
  """,
  "doc_summaries": """
    CREATE TABLE IF NOT EXISTS doc_summaries(
      url TEXT PRIMARY KEY REFERENCES docs(url) ON DELETE CASCADE,
      summary TEXT,
      ts_utc INTEGER
    );
  """,
  "evidence": """
    CREATE TABLE IF NOT EXISTS evidence(
      id INTEGER PRIMARY KEY,
      url TEXT REFERENCES docs(url) ON DELETE CASCADE,
      page_no INTEGER,
      quote TEXT,
      note TEXT,
      ts_utc INTEGER DEFAULT (strftime('%s','now'))
    );
  """,
}

TRIGGERS = {
  "docs_ai": """
    CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
      INSERT INTO docs_fts(rowid, title, content, url)
      VALUES (new.rowid, new.title, new.content, new.url);
    END;
  """,
  "docs_ad": """
    CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
      INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
      VALUES('delete', old.rowid, old.title, old.content, old.url);
    END;
  """,
  "docs_au": """
    CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
      INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
      VALUES('delete', old.rowid, old.title, old.content, old.url);
      INSERT INTO docs_fts(rowid, title, content, url)
      VALUES (new.rowid, new.title, new.content, new.url);
    END;
  """,
  "doc_pages_ai": """
    CREATE TRIGGER IF NOT EXISTS doc_pages_ai AFTER INSERT ON doc_pages BEGIN
      INSERT INTO pages_fts(rowid, text, url, page_no)
      VALUES (new.id, new.text, new.url, new.page_no);
    END;
  """,
  "doc_pages_ad": """
    CREATE TRIGGER IF NOT EXISTS doc_pages_ad AFTER DELETE ON doc_pages BEGIN
      INSERT INTO pages_fts(pages_fts, rowid, text, url, page_no)
      VALUES('delete', old.id, old.text, old.url, old.page_no);
    END;
  """,
  "doc_pages_au": """
    CREATE TRIGGER IF NOT EXISTS doc_pages_au AFTER UPDATE ON doc_pages BEGIN
      INSERT INTO pages_fts(pages_fts, rowid, text, url, page_no)
      VALUES('delete', old.id, old.text, old.url, old.page_no);
      INSERT INTO pages_fts(rowid, text, url, page_no)
      VALUES (new.id, new.text, new.url, new.page_no);
    END;
  """,
}

def table_info(c, name):
  return c.execute(f"PRAGMA table_info({name})").fetchall()

def has_column(c, table, col):
  return any(r[1] == col for r in table_info(c, table))

def ensure_columns(c, actions):
  # Add columns to docs if missing
  if not has_column(c, "docs", "kind"):
    c.execute("ALTER TABLE docs ADD COLUMN kind TEXT DEFAULT 'html'")
    actions.append("added:docs.kind")
  if not has_column(c, "docs", "page_count"):
    c.execute("ALTER TABLE docs ADD COLUMN page_count INTEGER DEFAULT 0")
    actions.append("added:docs.page_count")

def ensure_objects(c, actions):
  for name, sql in DDL.items():
    c.execute(sql)
    actions.append(f"ensure:{name}")
  for name, sql in TRIGGERS.items():
    c.execute(sql)
    actions.append(f"ensure:trigger:{name}")

def maybe_seed_fts(c, actions):
  # Seed docs_fts if empty but docs has rows
  n_docs = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
  n_fts  = c.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0]
  if n_docs > 0 and n_fts == 0:
    c.execute("INSERT INTO docs_fts(rowid, title, content, url) SELECT rowid, IFNULL(title,''), IFNULL(content,''), url FROM docs;")
    actions.append("seed:docs_fts")

  # Rebuild pages_fts if doc_pages exists but pages_fts is empty
  try:
    n_pages = c.execute("SELECT COUNT(*) FROM doc_pages").fetchone()[0]
    n_pfts  = c.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
    if n_pages > 0 and n_pfts == 0:
      c.execute("INSERT INTO pages_fts(rowid,text,url,page_no) SELECT id,text,url,page_no FROM doc_pages;")
      actions.append("seed:pages_fts")
  except sqlite3.OperationalError:
    # tables may not exist yet—ignore; ensure_objects handles it
    pass

def ensure(db_path=DEFAULT_DB):
  actions = []
  with sqlite3.connect(db_path) as c:
    c.execute("PRAGMA foreign_keys=ON;")
    c.execute("PRAGMA journal_mode=DELETE;")
    c.execute("PRAGMA synchronous=FULL;")
    c.execute("BEGIN IMMEDIATE;")
    try:
      ensure_objects(c, actions)
      ensure_columns(c, actions)
      maybe_seed_fts(c, actions)
      c.execute("COMMIT;")
    except Exception as e:
      c.execute("ROLLBACK;")
      print(json.dumps({"ok": False, "error": str(e), "actions": actions}, ensure_ascii=False))
      raise
  print(json.dumps({"ok": True, "actions": actions}, ensure_ascii=False))

if __name__ == "__main__":
  db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
  ensure(db)
