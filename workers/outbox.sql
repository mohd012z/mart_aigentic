-- Transactional intent ledger. Outgoing Telegram sends remain at-least-once unless reconciled.
CREATE TABLE IF NOT EXISTS telegram_outbox (
  id TEXT PRIMARY KEY,
  update_id INTEGER NOT NULL,
  chat_id INTEGER NOT NULL,
  method TEXT NOT NULL CHECK(method IN ('sendMessage','answerCallbackQuery')),
  payload TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','sending','sent','uncertain','dead')),
  attempts INTEGER NOT NULL DEFAULT 0,
  lease_until INTEGER,
  worker_id TEXT,
  telegram_message_id INTEGER,
  last_error_code TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_telegram_outbox_state ON telegram_outbox(state,lease_until);
