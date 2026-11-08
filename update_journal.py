"""SQLite update journal with generation-fenced ownership and conservative delivery."""
import os
import sqlite3
import time
from contextlib import closing

def connect():
    c = sqlite3.connect(os.getenv("MART_CAMPAIGN_DB", "mart_campaigns.sqlite3"), timeout=10)
    c.execute("PRAGMA busy_timeout=10000")
    c.execute("""CREATE TABLE IF NOT EXISTS update_journal(
        id INTEGER PRIMARY KEY, state TEXT NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
        chat INTEGER, reply TEXT, updated REAL NOT NULL, generation INTEGER NOT NULL DEFAULT 0)""")
    c.execute("BEGIN IMMEDIATE")
    columns = {r[1] for r in c.execute("PRAGMA table_info(update_journal)")}
    if "generation" not in columns:
        c.execute("ALTER TABLE update_journal ADD COLUMN generation INTEGER NOT NULL DEFAULT 0")
    c.commit()
    return c

def claim(uid, lease_seconds=120, now=None):
    if type(uid) is not int or uid < 0 or lease_seconds <= 0:
        raise ValueError("invalid update claim")
    now = time.time() if now is None else now
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT state,lease_until,generation FROM update_journal WHERE id=?", (uid,)).fetchone()
        if row is None:
            generation = 1
            c.execute("INSERT INTO update_journal(id,state,lease_until,updated,generation) VALUES(?,'processing',?,?,?)",
                      (uid, now + lease_seconds, now, generation))
            result = ("process", generation)
        elif row[0] == "processing" and row[1] <= now:
            generation = row[2] + 1
            c.execute("UPDATE update_journal SET lease_until=?,updated=?,generation=? WHERE id=?",
                      (now + lease_seconds, now, generation, uid))
            result = ("process", generation)
        else:
            result = (row[0], None)
        c.commit()
        return result

def prepare(uid, generation, chat, reply):
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        changed = c.execute("""UPDATE update_journal SET state='reply_pending',chat=?,reply=?,updated=?
            WHERE id=? AND generation=? AND state='processing' AND lease_until>?""",
            (chat, reply, time.time(), uid, generation, time.time())).rowcount
        c.commit()
        if changed != 1:
            raise RuntimeError("stale or expired update owner")

def begin_delivery(uid, generation):
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        now = time.time()
        changed = c.execute("""UPDATE update_journal SET state='delivery_uncertain',updated=?
            WHERE id=? AND generation=? AND state='reply_pending' AND lease_until>?""",
            (now, uid, generation, now)).rowcount
        c.commit()
        return changed == 1

def delivered(uid, generation):
    with closing(connect()) as c:
        c.execute("BEGIN IMMEDIATE")
        changed = c.execute("""UPDATE update_journal SET state='delivered',updated=?
            WHERE id=? AND generation=? AND state='delivery_uncertain'""",
            (time.time(), uid, generation)).rowcount
        c.commit()
        return changed == 1

def recoverable(now=None):
    now = time.time() if now is None else now
    with closing(connect()) as c:
        return c.execute("""SELECT id,state FROM update_journal
            WHERE (state='processing' AND lease_until<=?) OR state IN ('reply_pending','delivery_uncertain')
            ORDER BY id""", (now,)).fetchall()
