"""Verified-offer catalog for MART. Never invent affiliate rates or links."""
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit

ADD_DISCLOSURE = (
    "Affiliate disclosure: We may earn a commission from qualifying purchases. "
    "Rates and links below come from the verified catalog; confirm before publishing."
)

def validate_url(url):
    p=urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise ValueError("Only HTTPS offer URLs without embedded credentials are accepted")
    if p.hostname in ("localhost",) or p.hostname.endswith((".local",".internal")):
        raise ValueError("Local hosts are not allowed")
    return url

def _ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (
      id INTEGER PRIMARY KEY, merchant TEXT NOT NULL, title TEXT NOT NULL,
      url TEXT NOT NULL UNIQUE, source_url TEXT NOT NULL,
      disclosure TEXT NOT NULL, commission_text TEXT, category TEXT NOT NULL DEFAULT 'general',
      verified_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)""")
    if "category" not in {r[1] for r in conn.execute("PRAGMA table_info(offers)")}:
        conn.execute("ALTER TABLE offers ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
    conn.commit()

def init(db):
    with closing(sqlite3.connect(db)) as conn:
        _ensure_schema(conn)

def add_offer(db, merchant, title, url, source_url, verified_at, commission_text=None, category="general"):
    for field in (merchant,title,verified_at):
        if not field or not field.strip():
            raise ValueError("Merchant, title and verification date are required")
    validate_url(url)
    validate_url(source_url)
    init(db)
    with closing(sqlite3.connect(db)) as conn:
        cur=conn.execute("""INSERT INTO offers
            (merchant,title,url,source_url,disclosure,commission_text,category,verified_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (merchant[:120],title[:200],url,source_url,
             ADD_DISCLOSURE,commission_text,category[:32],verified_at))
        conn.commit()
        return cur.lastrowid

def list_offers(db, limit=10, category=None):
    init(db)
    with closing(sqlite3.connect(db)) as conn:
        conn.row_factory=sqlite3.Row
        if category:
            rows=conn.execute("""SELECT id,merchant,title,url,source_url,disclosure,
                commission_text,category,verified_at FROM offers
                WHERE active=1 AND category=? ORDER BY id DESC LIMIT ?""",
                (category, max(1,min(int(limit),50)))).fetchall()
        else:
            rows=conn.execute("""SELECT id,merchant,title,url,source_url,disclosure,
                commission_text,category,verified_at FROM offers WHERE active=1
                ORDER BY id DESC LIMIT ?""",(max(1,min(int(limit),50)),)).fetchall()
        return [dict(r) for r in rows]

def seed_from_file(db, path):
    """Idempotently load a JSON seed into the catalog.

    JSON shape: {"<category>": [{merchant,title,url,source_url,
    commission_text,verified_at}, ...]}. Existing URLs are left untouched, so
    re-seeding never duplicates and never overwrites a user's own edits.
    Returns the number of newly inserted offers.
    """
    import json, os
    if not path or not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    inserted = 0
    with closing(sqlite3.connect(db)) as conn:
        _ensure_schema(conn)
        existing = {r[0] for r in conn.execute("SELECT url FROM offers")}
        for category, offers in (data or {}).items():
            for o in offers:
                url = o.get("url", "")
                if not url or url in existing:
                    continue
                try:
                    add_offer(db,
                        merchant=o.get("merchant", "affiliate"),
                        title=o.get("title", o.get("merchant", "affiliate")),
                        url=url,
                        source_url=o.get("source_url", url),
                        verified_at=o.get("verified_at", "unverified"),
                        commission_text=o.get("commission_text"),
                        category=category)
                except ValueError:
                    # Reject a bad seed row but keep seeding the rest.
                    continue
                existing.add(url)
                inserted += 1
    return inserted
