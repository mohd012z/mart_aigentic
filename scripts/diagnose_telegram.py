"""Read-only Telegram Bot API diagnostic; never prints tokens or private URLs."""
import asyncio
import os
import httpx

METHODS = ("getMe", "getWebhookInfo", "getMyCommands")

def summarize(method, payload):
    if not payload.get("ok"):
        return {"method": method, "ok": False, "error_code": payload.get("error_code")}
    data = payload.get("result")
    if method == "getMe":
        return {"method": method, "ok": True, "username": data.get("username"), "is_bot": data.get("is_bot")}
    if method == "getWebhookInfo":
        return {"method": method, "ok": True, "webhook_configured": bool(data.get("url")),
                "pending_update_count": data.get("pending_update_count", 0),
                "last_error_date": data.get("last_error_date"),
                "has_delivery_error": bool(data.get("last_error_message")),
                "allowed_updates": data.get("allowed_updates")}
    return {"method": method, "ok": True, "commands": [x.get("command") for x in data]}

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing")
    async with httpx.AsyncClient(timeout=15) as client:
        for method in METHODS:
            try:
                response = await client.post(f"https://api.telegram.org/bot{token}/{method}")
                response.raise_for_status()
                result = summarize(method, response.json())
                print(result)
                if not result["ok"]:
                    raise SystemExit(1)
            except httpx.HTTPError as exc:
                print({"method": method, "error_type": type(exc).__name__})
                raise SystemExit(1) from None

if __name__ == "__main__":
    asyncio.run(main())
