"""Forex no-deposit bonus catalog for MART.

Bonuses are curated DATA with a source and a verified date — never invented.
list_bonuses filters to entries whose validity has not passed as of the given day,
so the bot can always say "list all" while staying honest about expiry.
"""
import sqlite3
from contextlib import closing

DEFAULT_VERIFIED = "2026-11-11"

# Curated seed: aggregator-verified no-deposit offers as of 2026-11-11.
# Each row: (broker, amount_text, eligibility, validity, source_url)
SEED = [
    ("XM", "$30", "new verified clients", "", "https://fxscouts.com/forex-brokers/bonuses/"),
    ("Tickmill", "$30", "new clients (welcome account, 60-day limit, 5-lot requirement)", "", "https://fxscouts.com/forex-brokers/bonuses/"),
    ("YWO", "$100", "new traders", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("WINPROFX", "$100", "new traders", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("ACIDFIRM", "$10,000", "all traders (free challenge)", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("RocketX", "$35", "all traders", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("STMarket", "$30", "new clients", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("Liquid Brokers", "$30", "new clients (sign-up bonus)", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("FXBITI", "$30", "new traders", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
    ("Ferminux", "$5", "new clients", "2026-12-31", "https://www.forexing.com/forex-no-deposit-bonus"),
]

DISCLAIMER = (
    "⚠️ No-deposit bonuses change without notice and usually carry turnover / "
    "verification / time limits. Always confirm the current terms on the broker's "
    "site before opening an account. This list is a lead, not an offer."
)


def _conn(db):
    c = sqlite3.connect(db, timeout=10)
    c.execute(
        """CREATE TABLE IF NOT EXISTS no_deposit_bonuses (
           id INTEGER PRIMARY KEY, broker TEXT NOT NULL,
           amount_text TEXT NOT NULL, eligibility TEXT NOT NULL,
           validity TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL,
           verified_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)""")
    c.commit()
    return c


def seed(db):
    """Insert the curated seed only if the table is empty (never duplicates)."""
    with closing(_conn(db)) as c:
        count = c.execute("SELECT COUNT(*) FROM no_deposit_bonuses").fetchone()[0]
        if count:
            return 0
        for broker, amount, eligibility, validity, source in SEED:
            c.execute(
                "INSERT INTO no_deposit_bonuses (broker,amount_text,eligibility,validity,source_url,verified_at) "
                "VALUES (?,?,?,?,?,?)",
                (broker[:120], amount[:40], eligibility[:200], validity[:10], source[:500], DEFAULT_VERIFIED))
        c.commit()
        return len(SEED)


def add_bonus(db, broker, amount_text, eligibility, validity, source_url, verified_at=None):
    if not broker or not broker.strip():
        raise ValueError("Broker name is required")
    with closing(_conn(db)) as c:
        cur = c.execute(
            "INSERT INTO no_deposit_bonuses (broker,amount_text,eligibility,validity,source_url,verified_at) "
            "VALUES (?,?,?,?,?,?)",
            (broker.strip()[:120], (amount_text or "").strip()[:40] or "n/a",
             (eligibility or "not stated")[:200], (validity or "").strip()[:10],
             source_url[:500], verified_at or DEFAULT_VERIFIED))
        c.commit()
        return cur.lastrowid


def list_bonuses(db, as_of=None, limit=50):
    """Return active bonuses with validity >= as_of (empty validity = ongoing)."""
    with closing(_conn(db)) as c:
        c.row_factory = sqlite3.Row
        as_of = as_of or DEFAULT_VERIFIED
        rows = c.execute(
            """SELECT broker, amount_text, eligibility, validity, source_url, verified_at
               FROM no_deposit_bonuses WHERE active=1
               AND (validity='' OR validity>=?) ORDER BY verified_at DESC, broker ASC LIMIT ?""",
            (as_of, max(1, min(int(limit), 50)))).fetchall()
        return [dict(r) for r in rows]
