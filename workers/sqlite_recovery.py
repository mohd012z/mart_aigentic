"""Offline SQLite reference implementation for MART inbox/outbox atomicity.

This module never calls Telegram, Cloudflare, or the legacy SQLite campaign deduplicator.
Production D1 parity must be verified before enabling the live D1 consumer.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS telegram_updates(
 update_id INTEGER PRIMARY KEY, payload TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt_at INTEGER NOT NULL DEFAULT 0, lease_until INTEGER,
 worker_id TEXT, created_at INTEGER NOT NULL DEFAULT (unixepoch()),
 updated_at INTEGER NOT NULL DEFAULT (unixepoch()));
CREATE TABLE IF NOT EXISTS telegram_outbox(
 id TEXT PRIMARY KEY, update_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
 method TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0, lease_until INTEGER, worker_id TEXT,
 created_at INTEGER NOT NULL DEFAULT (unixepoch()),
 updated_at INTEGER NOT NULL DEFAULT (unixepoch()));
"""

def connect(path):
    db = sqlite3.connect(str(Path(path)), timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.executescript(SCHEMA)
    return db

def ingest(db, update):
    uid = update.get("update_id")
    if type(uid) is not int or uid < 0 or uid > 9007199254740991:
        raise ValueError("Invalid update id")
    with db:
        return db.execute(
            "INSERT OR IGNORE INTO telegram_updates(update_id,payload) VALUES(?,?)",
            (uid, json.dumps(update, separators=(",", ":")))).rowcount == 1

def claim(db, now=None, owner=None, max_attempts=5, lease_seconds=120):
    now = int(time.time()) if now is None else now
    owner = owner or uuid.uuid4().hex
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("""UPDATE telegram_updates SET status='processing',
            attempts=attempts+1,worker_id=?,lease_until=?,updated_at=?
            WHERE update_id=(SELECT update_id FROM telegram_updates
              WHERE attempts<? AND ((status='pending' AND next_attempt_at<=?)
                OR (status='processing' AND lease_until<=?))
              ORDER BY created_at,update_id LIMIT 1)
            RETURNING update_id,payload,attempts,worker_id,lease_until""",
            (owner, now+lease_seconds, now, max_attempts, now, now)).fetchone()
        db.execute("COMMIT")
        return dict(row) if row else None
    except BaseException:
        db.execute("ROLLBACK")
        raise

def render(update):
    """Side-effect-free commands. Unsupported commands fail closed."""
    callback = update.get("callback_query")
    if callback:
        callback_id = callback.get("id")
        if not isinstance(callback_id, str) or not callback_id:
            return []
        return [("answerCallbackQuery", 0, {"callback_query_id": callback_id})]
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text", "").strip()
    if type(chat_id) is not int or not text:
        return []
    command = text.split(None, 1)[0].split("@", 1)[0].lower()
    if command in ("/start", "/help", "/menu"):
        response = "MART Research Bot\\n/research <topic>\\n/recommend <topic>\\n/status\\n/help"
    elif command == "/status":
        response = "Recovery service online. Research commands are not enabled in this offline adapter."
    else:
        response = "Command pending D1-safe integration; no external action performed."
    return [("sendMessage", chat_id, {"chat_id": chat_id, "text": response})]

def complete_with_outbox(db, row, messages, now=None):
    """Atomic lease-fenced completion and deterministic outbox intent creation."""
    now = int(time.time()) if now is None else now
    db.execute("BEGIN IMMEDIATE")
    try:
        current = db.execute("""SELECT update_id FROM telegram_updates
          WHERE update_id=? AND worker_id=? AND status='processing'
          AND lease_until>=?""", (row["update_id"], row["worker_id"], now)).fetchone()
        if current is None:
            raise RuntimeError("Lease lost; no outbox messages committed")
        for index, (method, chat_id, payload) in enumerate(messages):
            if method not in ("sendMessage", "answerCallbackQuery"):
                raise ValueError("Unsupported Telegram method")
            db.execute("""INSERT OR IGNORE INTO telegram_outbox(
              id,update_id,chat_id,method,payload)
              VALUES(?,?,?,?,?)""", (
                f'{row["update_id"]}:{index}:{method}', row["update_id"],
                chat_id, method, json.dumps(payload, separators=(",", ":"))))
        changed = db.execute("""UPDATE telegram_updates SET status='completed',
          worker_id=NULL,lease_until=NULL,updated_at=?
          WHERE update_id=? AND worker_id=? AND status='processing'
          AND lease_until>=?""", (now, row["update_id"], row["worker_id"], now)).rowcount
        if changed != 1:
            raise RuntimeError("Lease lost during completion")
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise

def process_once(db, now=None, owner=None):
    row = claim(db, now=now, owner=owner)
    if row is None:
        return "idle"
    complete_with_outbox(db, row, render(json.loads(row["payload"])), now=now)
    return "completed"
