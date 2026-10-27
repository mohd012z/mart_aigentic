"""Telegram webhook receiver. Requires HTTPS reverse proxy and a persistent ASGI host."""
import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from mart_engine import research
from telegram_ui import ACTIONS, keyboard, menu_text
from observability import record, report
import campaigns
from voice_intake import transcribe_telegram_voice, parse_command, VoiceError
import time

app = FastAPI(title="MART Agentic Research")

HELP = ("MART Research Bot\n"
        "/research <topic> — source-backed web research\n"
        "/recommend <topic> — evidence and recommendation brief\n"
        "/status — service configuration status\n"
        "/help — commands")

async def send_message(chat_id, message, menu=False):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4096], "disable_web_page_preview": True, **({"reply_markup": keyboard()} if menu else {})})
        response.raise_for_status()

@app.get("/health")
async def health():
    return {"status": "ok", "research_provider_configured": bool(os.getenv("BRAVE_SEARCH_API_KEY"))}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    import hmac
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not secret or not hmac.compare_digest(x_telegram_bot_api_secret_token or "", secret):
        raise HTTPException(status_code=403, detail="Forbidden")
    update = await request.json()
    if "update_id" in update and not campaigns.accept_update(update["update_id"]):
        return {"ok": True}
    callback = update.get("callback_query")
    if callback:
        await answer_callback(callback)
        return {"ok": True}
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    content = message.get("text", "").strip()
    voice = message.get("voice")
    if voice and chat_id:
        try:
            transcript = await transcribe_telegram_voice(voice.get("file_id"), voice.get("duration"))
            action, topic = parse_command(transcript)
            if action == "confirm":
                await send_message(chat_id, "Heard: " + transcript[:500] + "\nCommand not recognized. Send /research <topic> or /campaign <topic>.", menu=True)
                return {"ok": True}
            content = "/" + action + " " + topic
        except VoiceError:
            await send_message(chat_id, "Voice transcription unavailable. Please send a text command.", menu=True)
            return {"ok": True}

    if not chat_id or not content:
        return {"ok": True}
    cmd, _, arg = content.partition(" ")
    cmd = cmd.split("@", 1)[0].lower()
    if cmd == "/campaign":
        if arg.strip():
            cid = campaigns.create(chat_id, arg.strip())
            answer = f"Campaign queued: {cid}. Use /campaignstatus {cid} to check. Publishing requires approval."
        else:
            campaigns.select(chat_id, message.get("from", {}).get("id"), "campaign")
            answer = "Send the product or business topic to start a campaign."
    elif cmd == "/campaignstatus":
        row = campaigns.get(arg.strip(), chat_id)
        answer = f"Campaign {arg.strip()}: {row[0]}\\n{row[1][:3200]}" if row else "Campaign not found."
    elif not content.startswith("/") and campaigns.consume(chat_id, message.get("from", {}).get("id")) == "campaign":
        cid = campaigns.create(chat_id, content)
        answer = f"Campaign queued: {cid}. Use /campaignstatus {cid} to check."
    elif cmd in ("/start", "/help", "/menu"):
        answer = HELP
    elif cmd in ("/usage", "/quality", "/agentstatus", "/report"):
        answer = report()
    elif cmd == "/status":
        answer = "Service online. Research provider: " + ("configured" if os.getenv("BRAVE_SEARCH_API_KEY") else "missing")
    elif cmd.lstrip("/") in ACTIONS:
        kind = cmd.lstrip("/")
        if not arg.strip():
            answer = "Use /" + kind + " followed by a product or topic."
        elif kind in ("research", "recommend", "affiliate"):
            started = time.monotonic()
            try:
                answer = await research(arg.strip())
                record("research", provider="brave", status="ok" if not answer.startswith(("Research unavailable", "Research provider not configured")) else "failed", latency_ms=int((time.monotonic()-started)*1000))
            except Exception as exc:
                record("research", provider="brave", status="failed", latency_ms=int((time.monotonic()-started)*1000), error_type=type(exc).__name__)
                raise
        else:
            answer = create_draft(kind, arg.strip())
    elif cmd in ("/research", "/recommend"):
        answer = await research(arg.strip()) if arg.strip() else "Usage: " + cmd + " <topic>"
    else:
        answer = HELP
    await send_message(chat_id, answer, menu=True)
    return {"ok": True}

async def answer_callback(callback):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    data = callback.get("data", "")
    kind = data.removeprefix("action:")
    chat_id = (callback.get("message") or {}).get("chat", {}).get("id")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
        r.raise_for_status()
    if chat_id:
        if kind == "campaign":
            user_id = (callback.get("from") or {}).get("id")
            campaigns.select(chat_id, user_id, "campaign")
            await send_message(chat_id, "Send a product or business topic to create a campaign.", menu=True)
        elif kind in ACTIONS:
            await send_message(chat_id, f"Selected: {ACTIONS[kind][0]}\nEnter /{kind} followed by your topic.", menu=True)
        else:
            await send_message(chat_id, menu_text(), menu=True)

def create_draft(kind, topic):
    topic = topic[:250]
    templates = {
        "marketing": "Define audience, positioning, two channels, test budget, conversion goal, and weekly review.",
        "ads": "Headline: Explore {topic}. Copy: Compare available options and learn what fits your needs. CTA: Learn more. Verify claims before publishing.",
        "social": "Post idea: Three considerations when choosing {topic}. Invite feedback and disclose affiliate relationships.",
        "video": "Vertical video: 0-3s hook; 3-12s problem; 12-25s three tips; 25-35s CTA. Use licensed media."
    }
    template = templates.get(kind, "Research affiliate products, disclose partnerships, and verify product claims.")
    return f"{kind.upper()} — {topic}\n\n" + template.replace("{topic}", topic)
