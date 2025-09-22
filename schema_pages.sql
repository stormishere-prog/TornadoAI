PRAGMA journal_mode=DELETE;
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;

-- Base docs table stays as-is; add columns if missing
CREATE TABLE IF NOT EXISTS docs(
  url TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  ts_utc INTEGER,
  source_trust INTEGER DEFAULT 0,
  sha256 TEXT,
  kind TEXT DEFAULT 'pdf',          -- 'pdf'|'html'
  page_count INTEGER DEFAULT 0
);

-- Summary per doc (short, cached)
CREATE TABLE IF NOT EXISTS doc_summaries(
  url TEXT PRIMARY KEY REFERENCES docs(url) ON DELETE CASCADE,
  summary TEXT,
  ts_utc INTEGER
);

-- Per-page text with stable rowid (needed for FTS content=)
CREATE TABLE IF NOT EXISTS doc_pages(
  id INTEGER PRIMARY KEY,          -- rowid
  url TEXT REFERENCES docs(url) ON DELETE CASCADE,
  page_no INTEGER,
  text TEXT
);

-- Full-text search over pages (fast page lookups)
DROP TABLE IF EXISTS pages_fts;
CREATE VIRTUAL TABLE pages_fts
USING fts5(text, url UNINDEXED, page_no UNINDEXED, content='doc_pages', content_rowid='id');

-- Sync triggers
DROP TRIGGER IF EXISTS doc_pages_ai;
CREATE TRIGGER doc_pages_ai AFTER INSERT ON doc_pages BEGIN
  INSERT INTO pages_fts(rowid, text, url, page_no)
  VALUES (new.id, new.text, new.url, new.page_no);
END;

DROP TRIGGER IF EXISTS doc_pages_ad;
CREATE TRIGGER doc_pages_ad AFTER DELETE ON doc_pages BEGIN
  INSERT INTO pages_fts(pages_fts, rowid, text, url, page_no)
  VALUES('delete', old.id, old.text, old.url, old.page_no);
END;

DROP TRIGGER IF EXISTS doc_pages_au;
CREATE TRIGGER doc_pages_au AFTER UPDATE ON doc_pages BEGIN
  INSERT INTO pages_fts(pages_fts, rowid, text, url, page_no)
  VALUES('delete', old.id, old.text, old.url, old.page_no);
  INSERT INTO pages_fts(rowid, text, url, page_no)
  VALUES (new.id, new.text, new.url, new.page_no);
END;

-- Evidence you tag manually or programmatically
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY,
  url TEXT REFERENCES docs(url) ON DELETE CASCADE,
  page_no INTEGER,
  quote TEXT,
  note TEXT,
  ts_utc INTEGER DEFAULT (strftime('%s','now'))
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_doc_pages_url_page ON doc_pages(url, page_no);
CREATE INDEX IF NOT EXISTS idx_evidence_url_page ON evidence(url, page_no);
