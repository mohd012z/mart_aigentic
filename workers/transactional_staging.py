"""Offline D1-compatible inbox/outbox transaction rehearsal using SQLite.
This module is a reference implementation, not a live D1 migration.
"""
import json
import sqlite3

def stage_command(conn,update_id,chat_id,method,payload,*,owner,now):
    """Atomically record a processed update and one outgoing message intent."""
    if method not in ('sendMessage','answerCallbackQuery'):
        raise ValueError('Unsupported Telegram method')
    if not owner:raise ValueError('Lease owner required')
    outbox_id=f'update:{update_id}:{method}'
    with conn:
        row=conn.execute("SELECT status,worker_id,lease_until FROM telegram_updates WHERE update_id=?",(update_id,)).fetchone()
        if row is None or row[0]!='processing' or row[1]!=owner or row[2] is None or row[2]<now:
            return False
        conn.execute("INSERT OR IGNORE INTO telegram_outbox(id,update_id,chat_id,method,payload,state) VALUES(?,?,?,?,?,'pending')",
            (outbox_id,update_id,chat_id,method,json.dumps(payload,sort_keys=True)))
        conn.execute("UPDATE telegram_updates SET status='completed',worker_id=NULL,lease_until=NULL WHERE update_id=? AND status='processing' AND worker_id=? AND lease_until>=?",(update_id,owner,now))
    return True

def initialize_sqlite(conn,schema_sql,outbox_sql):
    conn.executescript(schema_sql)
    conn.executescript(outbox_sql)
