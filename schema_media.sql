PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS media_refs(
  id        INTEGER PRIMARY KEY,
  page_url  TEXT,               -- the HTML page where we saw the video link
  media_url TEXT UNIQUE,        -- the actual video URL
  mime      TEXT,               -- guessed/observed type (video/mp4, application/vnd.apple.mpegurl, etc.)
  ts_utc    INTEGER DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_media_ts ON media_refs(ts_utc);
CREATE INDEX IF NOT EXISTS idx_media_page ON media_refs(page_url);
