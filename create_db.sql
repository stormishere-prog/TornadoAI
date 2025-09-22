PRAGMA journal_mode=DELETE;
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;

DROP TABLE IF EXISTS docs;
CREATE TABLE docs(
  url TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  ts_utc INTEGER,
  source_trust INTEGER DEFAULT 0,
  sha256 TEXT
);

DROP TABLE IF EXISTS docs_fts;
CREATE VIRTUAL TABLE docs_fts
USING fts5(
  title,
  content,
  url UNINDEXED,
  content='docs',
  content_rowid='rowid'
);

-- Keep FTS in sync with docs:
DROP TRIGGER IF EXISTS docs_ai;
CREATE TRIGGER docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(rowid, title, content, url)
  VALUES (new.rowid, new.title, new.content, new.url);
END;

DROP TRIGGER IF EXISTS docs_ad;
CREATE TRIGGER docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
  VALUES('delete', old.rowid, old.title, old.content, old.url);
END;

DROP TRIGGER IF EXISTS docs_au;
CREATE TRIGGER docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, title, content, url)
  VALUES('delete', old.rowid, old.title, old.content, old.url);
  INSERT INTO docs_fts(rowid, title, content, url)
  VALUES (new.rowid, new.title, new.content, new.url);
END;
