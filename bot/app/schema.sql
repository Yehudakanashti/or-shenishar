PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  line          TEXT NOT NULL DEFAULT 'memorial',
  tagline       TEXT NOT NULL DEFAULT '',
  description   TEXT NOT NULL DEFAULT '',
  audience      TEXT NOT NULL DEFAULT '',
  price_from    INTEGER,
  price_to      INTEGER,
  lead_time     TEXT NOT NULL DEFAULT '',
  shipping      TEXT NOT NULL DEFAULT '',
  customization TEXT NOT NULL DEFAULT '',
  order_url     TEXT NOT NULL DEFAULT '',
  keywords      TEXT NOT NULL DEFAULT '[]',
  occasion      TEXT NOT NULL DEFAULT '',
  avoid         TEXT NOT NULL DEFAULT '',
  season_start  TEXT NOT NULL DEFAULT '',
  season_end    TEXT NOT NULL DEFAULT '',
  notes         TEXT NOT NULL DEFAULT '',
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_images (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  filename    TEXT NOT NULL,
  caption     TEXT NOT NULL DEFAULT '',
  is_primary  INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  text         TEXT NOT NULL,
  text_hash    TEXT NOT NULL UNIQUE,
  group_name   TEXT NOT NULL DEFAULT '',
  author_name  TEXT NOT NULL DEFAULT '',
  url          TEXT NOT NULL DEFAULT '',
  source       TEXT NOT NULL DEFAULT 'manual',
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS suggestions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id       INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  product_id    INTEGER REFERENCES products(id) ON DELETE SET NULL,
  image_id      INTEGER REFERENCES product_images(id) ON DELETE SET NULL,
  relevant      INTEGER NOT NULL DEFAULT 1,
  intent        TEXT NOT NULL DEFAULT '',
  sensitivity   TEXT NOT NULL DEFAULT 'neutral',
  confidence    REAL NOT NULL DEFAULT 0,
  comment_text  TEXT NOT NULL DEFAULT '',
  dm_text       TEXT NOT NULL DEFAULT '',
  reasoning     TEXT NOT NULL DEFAULT '',
  needs_human   INTEGER NOT NULL DEFAULT 1,
  policy_notes  TEXT NOT NULL DEFAULT '[]',
  status        TEXT NOT NULL DEFAULT 'pending',
  final_comment TEXT NOT NULL DEFAULT '',
  final_dm      TEXT NOT NULL DEFAULT '',
  engine        TEXT NOT NULL DEFAULT '',
  usage_in      INTEGER NOT NULL DEFAULT 0,
  usage_out     INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  decided_at    TEXT
);

CREATE TABLE IF NOT EXISTS examples (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,
  post_text  TEXT NOT NULL DEFAULT '',
  text       TEXT NOT NULL,
  origin     TEXT NOT NULL DEFAULT 'approved',
  active     INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocklist (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,
  value      TEXT NOT NULL,
  note       TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(kind, value)
);

CREATE TABLE IF NOT EXISTS events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,
  summary    TEXT NOT NULL DEFAULT '',
  payload    TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_suggestions_status  ON suggestions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_suggestions_post    ON suggestions(post_id);
CREATE INDEX IF NOT EXISTS idx_posts_author        ON posts(author_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_images_product      ON product_images(product_id, is_primary DESC);
CREATE INDEX IF NOT EXISTS idx_events_created      ON events(created_at DESC);

CREATE TABLE IF NOT EXISTS scheduled_posts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id    INTEGER REFERENCES products(id) ON DELETE SET NULL,
  image_id      INTEGER REFERENCES product_images(id) ON DELETE SET NULL,
  angle         TEXT NOT NULL DEFAULT '',
  text          TEXT NOT NULL DEFAULT '',
  scheduled_for TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT 'draft',
  fb_post_id    TEXT NOT NULL DEFAULT '',
  error         TEXT NOT NULL DEFAULT '',
  engine        TEXT NOT NULL DEFAULT '',
  policy_notes  TEXT NOT NULL DEFAULT '[]',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  published_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_status ON scheduled_posts(status, scheduled_for);
