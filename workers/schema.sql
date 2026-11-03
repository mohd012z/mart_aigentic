-- D1 durable inbox. Apply only to a development D1 database until deployment is approved.
CREATE TABLE IF NOT EXISTS telegram_updates (
 update_id INTEGER PRIMARY KEY,
 payload TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','completed','dead')),
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt_at INTEGER NOT NULL DEFAULT 0,
 lease_until INTEGER,
 worker_id TEXT,
 last_error_code TEXT,
 created_at INTEGER NOT NULL DEFAULT (unixepoch()),
 updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_telegram_updates_due ON telegram_updates(status,next_attempt_at,lease_until);
