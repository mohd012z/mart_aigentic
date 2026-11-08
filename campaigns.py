import os, sqlite3, time, uuid
from contextlib import closing
DB=os.getenv("MART_CAMPAIGN_DB","mart_campaigns.sqlite3")
def conn():
    c=sqlite3.connect(DB,timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,chat INTEGER,topic TEXT,status TEXT,output TEXT DEFAULT '')")
    c.execute("CREATE TABLE IF NOT EXISTS sessions(chat INTEGER,user INTEGER,action TEXT,PRIMARY KEY(chat,user))")
    c.execute("CREATE TABLE IF NOT EXISTS updates(id INTEGER PRIMARY KEY)")
    c.commit()
    return c
def accept_update(uid):
    with closing(conn()) as c:
        r=c.execute("INSERT OR IGNORE INTO updates VALUES(?)",(uid,));c.commit();return r.rowcount==1
def select(chat,user,action):
    with closing(conn()) as c:
        c.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?)",(chat,user,action));c.commit()
def consume(chat,user):
    with closing(conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("SELECT action FROM sessions WHERE chat=? AND user=?",(chat,user)).fetchone()
        c.execute("DELETE FROM sessions WHERE chat=? AND user=?",(chat,user));c.commit()
        return row[0] if row else None
def create(chat,topic,update_id=None):
    if not 1<=len(topic.strip())<=300: raise ValueError("Invalid topic")
    cid=(f'u{update_id:x}' if update_id is not None else uuid.uuid4().hex[:12])
    with closing(conn()) as c:
        c.execute("INSERT OR IGNORE INTO campaigns(id,chat,topic,status) VALUES(?,?,?,'queued')",(cid,chat,topic.strip()));c.commit()
    return cid
def claim():
    with closing(conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("SELECT id,chat,topic FROM campaigns WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
        if row:c.execute("UPDATE campaigns SET status='running' WHERE id=?",(row[0],))
        c.commit();return row
def finish(cid,output,success=True):
    with closing(conn()) as c:
        c.execute("UPDATE campaigns SET status=?,output=? WHERE id=? AND status='running'",("review" if success else "failed",output,cid));c.commit()
def get(cid,chat):
    with closing(conn()) as c:
        return c.execute("SELECT status,output FROM campaigns WHERE id=? AND chat=?",(cid,chat)).fetchone()

def consume_and_create(chat, user, topic, update_id):
    """Atomically consume campaign session and insert a retry-safe campaign."""
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 300:
        raise ValueError("Invalid topic")
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Invalid update ID")
    cid = f"u{update_id:x}"
    with closing(conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        existing = c.execute("SELECT chat,topic FROM campaigns WHERE id=?", (cid,)).fetchone()
        if existing:
            if existing != (chat, topic.strip()):
                raise ValueError("Update ID collision")
            c.commit()
            return cid
        row = c.execute("SELECT action FROM sessions WHERE chat=? AND user=?", (chat,user)).fetchone()
        if not row or row[0] != "campaign":
            c.commit()
            return None
        c.execute("INSERT INTO campaigns(id,chat,topic,status) VALUES(?,?,?,'queued')",
                  (cid,chat,topic.strip()))
        c.execute("DELETE FROM sessions WHERE chat=? AND user=?", (chat,user))
        c.commit()
        return cid
