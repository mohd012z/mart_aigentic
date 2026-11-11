"""Telegram webhook receiver. Requires HTTPS reverse proxy and a persistent ASGI host."""
import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from mart_engine import research, recommend, affiliate_brief
from drafts import create_draft
from telegram_ui import ACTIONS, keyboard, menu_text
from observability import record, report
import campaigns
import update_journal
import time

app = FastAPI(title="MART Agentic Research")

HELP = ("MART Research Bot — commands\n\n"
        "🔎 /research <topic> — source-backed web research\n"
        "📊 /recommend <topic> — evidence + initial signal score (0–100)\n"
        "🚀 /campaign <topic> — queue a campaign for review\n"
        "   /campaignstatus <id> — check a queued campaign\n"
        "📣 /marketing <topic> — marketing plan outline\n"
        "🎯 /ads <topic> — advertisement copy draft\n"
        "📱 /social <topic> — social content draft\n"
        "🎬 /video <topic> — short-video script draft\n"
        "🛍 /affiliate <topic> — verified offers + market evidence\n"
        "⚙️ /status — service configuration\n"
        "📈 /metrics — agent usage & cost ledger (also /usage /quality /agentstatus /report)\n"
        "❓ /help — this list\n\n"
        "🔒 Research mode: no automatic publishing or live campaign delivery.")

async def send_message(chat_id, message, menu=False):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4096], "disable_web_page_preview": True, **({"reply_markup": keyboard()} if menu else {})})
        response.raise_for_status()

def ensure_affiliate_seed(db):
    import affiliate_catalog
    import os
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seeds", "forex_affiliate.json")
    affiliate_catalog.seed_from_file(db, seed_path)

@app.get("/health")
async def health():
    return {"status": "ok", "research_provider_configured": bool(os.getenv("BRAVE_SEARCH_API_KEY"))}

def render_bonus_list(db):
    import forex_bonuses
    bonuses = forex_bonuses.list_bonuses(db)
    if not bonuses:
        return ("💵 Forex No-Deposit Bonus\n\n"
                "No active bonuses are stored right now. Use /forexbonus again later — "
                "the list is refreshed when offers are re-verified.")
    lines = ["💵 Forex No-Deposit Bonus — all current offers\n"]
    for i, b in enumerate(bonuses, 1):
        validity = b["validity"] or "ongoing (verify with broker)"
        lines.append(f"{i}. {b['broker']}: {b['amount_text']} — {b['eligibility']}\n   "
                     f"Valid: {validity} · verified {b['verified_at']}\n   {b['source_url']}")
    lines.append("\n" + forex_bonuses.DISCLAIMER)
    return "\n".join(lines)[:3900]

def render_forexa(db, chat_id, text=""):
    import affiliate_catalog
    import sqlite3
    import time as _t
    parts = [p for p in text.split() if p]
    verb = (parts[0].lower() if parts else "list")
    if verb in ("", "list", "all"):
        offers = affiliate_catalog.list_offers(db, limit=20, category="forex")
        if not offers:
            return (
                "🔗 Forex Affiliate Links\n\n"
                "No links stored yet.\n\n"
                "Add one (name = one word):\n"
                "/forexa add <name> <https://link>\n\n"
                "Examples:\n"
                "/forexa list — show all\n"
                "/forexa share <Name|number> — copyable share text\n"
                "/forexa remove <Name|number>")
        lines = [f"🔗 Your forex affiliate links ({len(offers)})\n"]
        for i, o in enumerate(offers, 1):
            lines.append(f"{i}. {o['merchant']} — {o['title']}\n{ o['url']}")
        lines.append("\n/forexa share <number or name> for copyable text · /forexa remove <number or name>")
        return "\n".join(lines)[:3900]
    if verb == "add":
        if len(parts) < 3:
            return "Usage: /forexa add <name> <https://link>\n(name = one word, e.g. fxprime or xm-my)"
        name = parts[1][:120]
        url = parts[2]
        if not url.startswith("https://"):
            return "The link must start with https:// — e.g. /forexa add xm https://broker.com/?partner=123"
        try:
            affiliate_catalog.add_offer(db, name, name, url, url,
                _t.strftime("%Y-%m-%d"), category="forex")
        except Exception:
            return "Could not store that link. It must be an https:// URL (e.g. https://broker.com/?partner=123)."
        return f"✅ Stored '{name}'.\n{url}\n\n/forexa list to see all · /forexa share {len(affiliate_catalog.list_offers(db, 20, 'forex'))} to share it."
    if verb == "share":
        offers = affiliate_catalog.list_offers(db, limit=20, category="forex")
        if not parts[1:]:
            return "Usage: /forexa share <number or name>"
        key = parts[1].lower()
        match = None
        for i, o in enumerate(offers, 1):
            if key == str(i) or o["merchant"].lower() == key or o["title"].lower() == key:
                match = o
                break
        if not match:
            return "Link not found. /forexa list to see numbers and names."
        return (
            f"Copy & share:\n\n"
            f"📈 {match['merchant']}: {match['title']}\n{match['url']}\n\n"
            + affiliate_catalog.ADD_DISCLOSURE
        )[:3900]
    if verb == "remove":
        offers = affiliate_catalog.list_offers(db, limit=20, category="forex")
        if not parts[1:]:
            return "Usage: /forexa remove <number or name>"
        key = parts[1].lower()
        with sqlite3.connect(db) as c:
            for i, o in enumerate(offers, 1):
                if key == str(i) or o["merchant"].lower() == key or o["title"].lower() == key:
                    c.execute("UPDATE offers SET active=0 WHERE id=?", (o["id"],))
                    c.commit()
                    return f"🗑 Removed '{o['merchant']}'."
        return "Link not found. /forexa list to see numbers and names."
    return "Forex affiliate links: /forexa list · /forexa add <Name> <url> · /forexa share <name> · /forexa remove <name>"

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    import hmac
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not secret or not hmac.compare_digest(x_telegram_bot_api_secret_token or "", secret):
        raise HTTPException(status_code=403, detail="Forbidden")
    update = await request.json()
    uid = update.get("update_id")
    if uid is None:
        raise HTTPException(status_code=400, detail="Missing update ID")
    state, generation = update_journal.claim(uid)
    if state != "process":
        return {"ok": True, "journal_state": state}
    callback = update.get("callback_query")
    if callback:
        chat = (callback.get("message") or {}).get("chat") or {}
        chat_id = chat.get("id")
        answer = await answer_callback(callback, send=False, acknowledge=False, select_session=False)
        if chat_id and answer:
            from_user = (callback.get("from") or {}).get("id")
            chat_type = chat.get("type")
            campaign_authorized = (callback.get("data") == "action:campaign"
                and chat_type == "private" and type(from_user) is int
                and type(chat_id) is int and from_user == chat_id)
            update_journal.prepare_callback(uid, generation, chat_id, answer,
                user=from_user if campaign_authorized else None,
                action="campaign" if campaign_authorized else None)
            await acknowledge_callback(callback)
            if update_journal.begin_delivery(uid, generation):
                await send_message(chat_id, answer, menu=True)
                update_journal.delivered(uid, generation)
        else:
            update_journal.prepare(uid, generation, chat_id, "")
            update_journal.begin_delivery(uid, generation)
            update_journal.delivered(uid, generation)
        return {"ok": True}
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    content = message.get("text", "").strip()
    if not chat_id or not content:
        update_journal.prepare(uid, generation, chat_id, "")
        update_journal.begin_delivery(uid, generation)
        update_journal.delivered(uid, generation)
        return {"ok": True}
    cmd, _, arg = content.partition(" ")
    cmd = cmd.split("@", 1)[0].lower()
    if cmd == "/campaign":
        if arg.strip():
            cid = campaigns.create(chat_id, arg.strip(), uid)
            answer = f"Campaign queued: {cid}. Use /campaignstatus {cid} to check. Publishing requires approval."
        else:
            campaigns.select(chat_id, message.get("from", {}).get("id"), "campaign")
            answer = "Send the product or business topic to start a campaign."
    elif cmd == "/campaignstatus":
        row = campaigns.get(arg.strip(), chat_id)
        answer = f"Campaign {arg.strip()}: {row[0]}\n{row[1][:3200]}" if row else "Campaign not found."
    elif not content.startswith("/"):
        cid = campaigns.consume_and_create(chat_id, message.get("from", {}).get("id"), content, uid)
        answer = f"Campaign queued: {cid}. Use /campaignstatus {cid} to check." if cid else HELP
    elif cmd in ("/start", "/menu"):
        answer = menu_text()
    elif cmd == "/help":
        answer = HELP
    elif cmd in ("/usage", "/quality", "/agentstatus", "/report", "/metrics"):
        answer = report()
    elif cmd == "/status":
        answer = "Service online. Research provider: " + ("configured" if os.getenv("BRAVE_SEARCH_API_KEY") else "missing")
    elif cmd == "/forexbonus":
        import forex_bonuses
        db = os.getenv("MART_BONUS_DB", "mart_bonuses.sqlite3")
        forex_bonuses.seed(db)
        answer = render_bonus_list(db)
    elif cmd == "/forexa":
        db = os.getenv("MART_AFFILIATE_DB", "mart_offers.sqlite3")
        ensure_affiliate_seed(db)
        from_user = message.get("from", {}).get("id")
        chat_type = (message.get("chat") or {}).get("type")
        if chat_type != "private" or not from_user or from_user != chat_id:
            answer = "Forex affiliate links are stored per private chat only. Use /forexa in your private chat with the bot."
        else:
            answer = render_forexa(db, chat_id, arg)
    elif cmd.lstrip("/") in ACTIONS:
        kind = cmd.lstrip("/")
        if not arg.strip():
            answer = "Use /" + kind + " followed by a product or topic."
        elif kind == "research":
            started = time.monotonic()
            try:
                answer = await research(arg.strip())
                record("research", provider="brave", status="ok" if not answer.startswith(("Research unavailable", "Research provider not configured")) else "failed", latency_ms=int((time.monotonic()-started)*1000))
            except Exception as exc:
                record("research", provider="brave", status="failed", latency_ms=int((time.monotonic()-started)*1000), error_type=type(exc).__name__)
                raise
        elif kind == "recommend":
            started = time.monotonic()
            try:
                answer = await recommend(arg.strip())
                record("recommend", provider="brave", status="ok" if not answer.startswith(("Research unavailable", "Research provider not configured")) else "failed", latency_ms=int((time.monotonic()-started)*1000))
            except Exception as exc:
                record("recommend", provider="brave", status="failed", latency_ms=int((time.monotonic()-started)*1000), error_type=type(exc).__name__)
                raise
        elif kind == "affiliate":
            started = time.monotonic()
            try:
                answer = await affiliate_brief(arg.strip(), os.getenv("MART_AFFILIATE_DB", "mart_offers.sqlite3"))
                record("affiliate", provider="brave+catalog", status="ok" if not answer.startswith(("Research unavailable", "Research provider not configured")) else "failed", latency_ms=int((time.monotonic()-started)*1000))
            except Exception as exc:
                record("affiliate", provider="brave+catalog", status="failed", latency_ms=int((time.monotonic()-started)*1000), error_type=type(exc).__name__)
                raise
        else:
            answer = create_draft(kind, arg.strip())
    elif cmd in ("/research", "/recommend"):
        answer = await (research if cmd == "/research" else recommend)(arg.strip()) if arg.strip() else "Usage: " + cmd + " <topic>"
    else:
        answer = HELP
    update_journal.prepare(uid, generation, chat_id, answer)
    if update_journal.begin_delivery(uid, generation):
        await send_message(chat_id, answer, menu=True)
        update_journal.delivered(uid, generation)
    return {"ok": True, "answer": (answer or "")[:400]}

async def acknowledge_callback(callback):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
            r.raise_for_status()
        except httpx.HTTPStatusError:
            pass  # already-answered/old query: non-fatal, update still handled

async def answer_callback(callback, send=True, acknowledge=True, select_session=True):
    if acknowledge:
        await acknowledge_callback(callback)
    data = callback.get("data", "")
    kind = data.removeprefix("action:")
    chat_id = (callback.get("message") or {}).get("chat", {}).get("id")
    if not chat_id:
        return None
    if kind == "campaign":
        user_id = (callback.get("from") or {}).get("id")
        chat_type = ((callback.get("message") or {}).get("chat") or {}).get("type")
        if chat_type != "private" or not user_id or user_id != chat_id:
            message = "Campaign creation is available in your private chat only."
        else:
            if select_session:
                campaigns.select(chat_id, user_id, "campaign")
            message = "Send a product or business topic to create a campaign."
    elif kind in ACTIONS:
        message = f"Selected: {ACTIONS[kind][0]}\nEnter /{kind} followed by your topic."
    elif data == "status":
        message = "Service online. Research provider: " + ("configured" if os.getenv("BRAVE_SEARCH_API_KEY") else "missing")
    elif data == "help":
        message = HELP
    else:
        message = menu_text()
    if send:
        await send_message(chat_id, message, menu=True)
    return message
