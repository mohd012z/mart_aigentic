"""Telegram webhook receiver. Requires HTTPS reverse proxy and a persistent ASGI host."""
import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from mart_engine import research

app = FastAPI(title="MART Agentic Research")

HELP = ("MART Research Bot\n"
        "/research <topic> — source-backed web research\n"
        "/recommend <topic> — evidence and recommendation brief\n"
        "/status — service configuration status\n"
        "/help — commands")

async def send_message(chat_id, message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4096], "disable_web_page_preview": True})
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
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    content = message.get("text", "").strip()
    if not chat_id or not content:
        return {"ok": True}
    cmd, _, arg = content.partition(" ")
    cmd = cmd.split("@", 1)[0].lower()
    if cmd in ("/start", "/help"):
        answer = HELP
    elif cmd == "/status":
        answer = "Service online. Research provider: " + ("configured" if os.getenv("BRAVE_SEARCH_API_KEY") else "missing")
    elif cmd in ("/research", "/recommend"):
        answer = await research(arg.strip()) if arg.strip() else "Usage: " + cmd + " <topic>"
    else:
        answer = HELP
    await send_message(chat_id, answer)
    return {"ok": True}
