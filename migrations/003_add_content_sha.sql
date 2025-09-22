PRAGMA foreign_keys=OFF;
BEGIN;
ALTER TABLE docs ADD COLUMN content_sha TEXT ;
CREATE UNIQUE INDEX IF NOT EXISTS idx_docs_content_sha ON docs(content_sha);
COMMIT;
