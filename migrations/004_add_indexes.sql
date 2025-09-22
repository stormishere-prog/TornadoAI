CREATE INDEX IF NOT EXISTS idx_docs_ts         ON docs(ts_utc);
CREATE INDEX IF NOT EXISTS idx_docs_doc_type   ON docs(doc_type);
CREATE INDEX IF NOT EXISTS idx_docs_type_ts    ON docs(doc_type, ts_utc DESC);
CREATE INDEX IF NOT EXISTS idx_docs_source_tag ON docs(source_tag);
CREATE INDEX IF NOT EXISTS idx_pages_url_no    ON doc_pages(url, page_no);
