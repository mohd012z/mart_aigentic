"""Durable, conservative Telegram update journal.

An outbound request that may have reached Telegram is never blindly retried.
Operators must reconcile delivery_uncertain records manually.
"""
import os
import sqlite3
import time
from contextlib import closing

DB_ENV = "MART_CAMPAIGN_DB"

def connect():
    db = os.getenv(DB_ENV, "mart_campaigns.sqlite3")
    c = sqlite3.connect(db, timeout=10)
    c.execute("PRAGMA busy_timeout=10000")
    c.execute("""CREATE TABLE IF NOT EXISTS update_journal(
        id INTEGER PRIMARY KEY, state TEXT NOT NULL,
        lease_until REAL NOT NULL DEFAULT 0,
        chat INTEGER, reply TEXT, updated REAL NOT NULL)""")
    c.commit()
    return c

def claim(uid, lease_seconds=120, now=None):
    if not isinstance(uid, int) or isinstance(uid, bool):
        raise ValueError("invalid update ID")
    now = time.time() if now is None else now
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT state,lease_until FROM update_journal WHERE id=?", (uid,)).fetchone()
        if row is None:
            c.execute("INSERT INTO update_journal(id,state,lease_until,updated) VALUES(?,'processing',?,?)",
                      (uid, now + lease_seconds, now))
            outcome = "process"
        elif row[0] == "processing" and row[1] <= now:
            c.execute("UPDATE update_journal SET lease_until=?,updated=? WHERE id=?",
                      (now + lease_seconds, now, uid))
            outcome = "process"
        else:
            outcome = row[0]
        c.commit()
        return outcome

def prepare(uid, chat, reply):
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        changed = c.execute("""UPDATE update_journal SET state='reply_pending',chat=?,reply=?,updated=?
            WHERE id=? AND state='processing'""", (chat, reply, time.time(), uid)).rowcount
        c.commit()
        if changed != 1:
            raise RuntimeError("update lease state changed")

def begin_delivery(uid):
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        changed = c.execute("""UPDATE update_journal SET state='delivery_uncertain',updated=?
            WHERE id=? AND state='reply_pending'""", (time.time(), uid)).rowcount
        c.commit()
        return changed == 1

def delivered(uid):
    with closing(connect()) as c:
        c.execute("UPDATE update_journal SET state='delivered',updated=? WHERE id=? AND state='delivery_uncertain'",
                  (time.time(), uid))
        c.commit()

def recoverable(now=None):
    now = time.time() if now is None else now
    with closing(connect()) as c:
        return c.execute("""SELECT id,state FROM update_journal
            WHERE (state='processing' AND lease_until<=?) OR state IN ('reply_pending','delivery_uncertain')
            ORDER BY id""", (now,)).fetchall()
