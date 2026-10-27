"""Verified-offer catalog for MART. Never invent affiliate rates or links."""
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit

def validate_url(url):
    p=urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ValueError("Only HTTPS offer URLs without embedded credentials are accepted")
    if p.hostname in ("localhost",) or p.hostname.endswith((".local",".internal")):
        raise ValueError("Local hosts are not allowed")
    return url

def init(db):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS offers (
          id INTEGER PRIMARY KEY, merchant TEXT NOT NULL, title TEXT NOT NULL,
          url TEXT NOT NULL UNIQUE, source_url TEXT NOT NULL,
          disclosure TEXT NOT NULL, commission_text TEXT,
          verified_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)""")
        conn.commit()

def add_offer(db, merchant, title, url, source_url, verified_at, commission_text=None):
    for field in (merchant,title,verified_at):
        if not field or not field.strip():
            raise ValueError("Merchant, title and verification date are required")
    validate_url(url)
    validate_url(source_url)
    init(db)
    with closing(sqlite3.connect(db)) as conn:
        cur=conn.execute("""INSERT INTO offers
            (merchant,title,url,source_url,disclosure,commission_text,verified_at)
            VALUES (?,?,?,?,?,?,?)""",
            (merchant[:120],title[:200],url,source_url,
             "Affiliate disclosure: We may earn a commission from qualifying purchases.",
             commission_text,verified_at))
        conn.commit()
        return cur.lastrowid

def list_offers(db, limit=10):
    init(db)
    with closing(sqlite3.connect(db)) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute("""SELECT id,merchant,title,url,source_url,disclosure,
            commission_text,verified_at FROM offers WHERE active=1
            ORDER BY id DESC LIMIT ?""",(max(1,min(int(limit),50)),)).fetchall()
        return [dict(r) for r in rows]
