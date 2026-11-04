"""Independent, draft-only affiliate copywriting for MART. No external publishing."""
import json
import re
import sqlite3
from urllib.parse import urlsplit
import campaigns

ANGLES = (
    ("Problem and solution", "Masalah dan penyelesaian"),
    ("Benefits", "Manfaat"),
    ("Product features", "Ciri produk"),
    ("Storytelling", "Penceritaan"),
    ("Question hook", "Soalan pembuka"),
    ("Practical use case", "Kegunaan praktikal"),
    ("Comparison considerations", "Pertimbangan perbandingan"),
    ("Short caption", "Kapsyen ringkas"),
    ("Educational explanation", "Penerangan pendidikan"),
    ("Call to action", "Ajakan bertindak"),
)
HOSTS = ("shopee.com.my", "shopee.sg", "shopee.co.id",
         "lazada.com.my", "lazada.sg", "lazada.co.id")
MAX_PRODUCT = 1200


def valid_product(raw):
    value = raw.strip()
    if not 1 <= len(value) <= MAX_PRODUCT or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    if re.match(r"^https?://", value, re.I):
        try:
            url = urlsplit(value)
            host = (url.hostname or "").lower()
            if (url.scheme != "https" or url.username or url.password or url.port
                    or url.fragment or host not in HOSTS
                    and not any(host.endswith("." + h) for h in HOSTS)):
                return None
            return value
        except ValueError:
            return None
    if re.search(r"https?://|www\\.", value, re.I):
        return None
    return value


def connect():
    db = sqlite3.connect(campaigns.DB, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS affiliate_settings (chat INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'ms', guidance TEXT NOT NULL DEFAULT '')")
    db.execute("CREATE TABLE IF NOT EXISTS affiliate_drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, chat INTEGER NOT NULL, product TEXT NOT NULL, language TEXT NOT NULL, variants TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    db.execute("CREATE INDEX IF NOT EXISTS affiliate_drafts_chat ON affiliate_drafts(chat,id DESC)")
    db.commit()
    return db


def settings(chat):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO affiliate_settings(chat) VALUES (?)", (chat,))
        return db.execute("SELECT language,guidance FROM affiliate_settings WHERE chat=?", (chat,)).fetchone()


def set_language(chat, language):
    if language not in ("ms", "en"):
        raise ValueError("Unsupported language")
    settings(chat)
    with connect() as db:
        db.execute("UPDATE affiliate_settings SET language=? WHERE chat=?", (language, chat))


def set_guidance(chat, guidance):
    if not 1 <= len(guidance.strip()) <= 800:
        raise ValueError("Guidance must contain 1–800 characters")
    settings(chat)
    with connect() as db:
        db.execute("UPDATE affiliate_settings SET guidance=? WHERE chat=?", (guidance.strip(), chat))


def generate(chat, raw):
    product = valid_product(raw)
    if product is None:
        raise ValueError("Invalid product. Enter a description or HTTPS Shopee/Lazada URL (up to 1200 characters).")
    language, guidance = settings(chat)
    disclosure = ("Pautan afiliasi: saya mungkin menerima komisen."
                  if language == "ms" else "Affiliate disclosure: I may earn a commission.")
    check = ("Sahkan harga, stok dan ciri produk sebelum siaran."
             if language == "ms" else "Verify price, availability and features before publishing.")
    variants = []
    for index, (en, ms) in enumerate(ANGLES, 1):
        angle = ms if language == "ms" else en
        prefix = "Sudut promosi" if language == "ms" else "Promotional angle"
        variants.append(f"{index}. {prefix}: {angle}\\n{product}\\n{check}\\n{disclosure}")
    with connect() as db:
        cursor = db.execute("INSERT INTO affiliate_drafts(chat,product,language,variants) VALUES (?,?,?,?)",
                            (chat, product, language, json.dumps(variants, ensure_ascii=False)))
        draft_id = cursor.lastrowid
    return draft_id, variants


def history(chat):
    with connect() as db:
        rows = db.execute("SELECT id,product,language FROM affiliate_drafts WHERE chat=? ORDER BY id DESC LIMIT 5",
                          (chat,)).fetchall()
    return "\\n".join(f"#{i} [{lang}] {p[:80]}" for i,p,lang in rows) or "No affiliate drafts saved."


def draft(chat, draft_id):
    with connect() as db:
        row = db.execute("SELECT variants FROM affiliate_drafts WHERE id=? AND chat=?",
                         (draft_id, chat)).fetchone()
    return json.loads(row[0]) if row else None
