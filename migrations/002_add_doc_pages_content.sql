PRAGMA foreign_keys=OFF;
BEGIN;
ALTER TABLE doc_pages ADD COLUMN content TEXT ;
COMMIT;
