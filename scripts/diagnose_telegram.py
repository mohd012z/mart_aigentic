"""Read-only MART Telegram Bot API diagnostics with redacted output."""
import asyncio
import os
import re
import httpx

METHODS = ("getMe", "getWebhookInfo", "getMyCommands")
EXPECTED_USERNAME = "mart_aigenticbot"
EXPECTED_COMMANDS = frozenset(("start", "menu", "campaign", "campaignstatus", "research", "recommend", "marketing", "ads", "social", "video", "affiliate", "forexbonus", "forexa", "status", "help"))


def classify_error(message):
    """Categorize delivery failures without revealing raw error messages."""
    text = (message or "").lower()
    if not text:
        return "none"
    if re.search(r"\b(401|403)\b|unauthorized|forbidden", text):
        return "authentication_or_forbidden"
    if re.search(r"\b404\b|not found", text):
        return "not_found"
    if re.search(r"\b(502|503|504)\b|bad gateway|service unavailable", text):
        return "upstream_unavailable"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "certificate" in text or "ssl" in text or "tls" in text:
        return "tls_error"
    if "connection" in text or "resolve" in text:
        return "connection_error"
    return "other"


def summarize(method, payload):
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return {"method": method, "ok": False, "error_code": payload.get("error_code") if isinstance(payload, dict) and isinstance(payload.get("error_code"), int) else None}
    data = payload.get("result")
    if method == "getMe":
        if not isinstance(data, dict):
            return {"method": method, "ok": False, "error_code": None}
        return {"method": method, "ok": True, "username_matches_expected": data.get("username") == EXPECTED_USERNAME, "is_bot": data.get("is_bot") is True}
    if method == "getWebhookInfo":
        if not isinstance(data, dict):
            return {"method": method, "ok": False, "error_code": None}
        allowed = data.get("allowed_updates")
        return {"method": method, "ok": True, "webhook_configured": bool(data.get("url")), "pending_update_count": data.get("pending_update_count"), "last_error_date": data.get("last_error_date"), "has_delivery_error": bool(data.get("last_error_message")), "delivery_error_category": classify_error(data.get("last_error_message")), "message_updates_allowed": allowed is None or "message" in allowed, "allowed_updates_present": allowed is not None}
    if method == "getMyCommands":
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            return {"method": method, "ok": False, "error_code": None}
        commands = {item.get("command") for item in data if isinstance(item.get("command"), str)}
        return {"method": method, "ok": True, "command_count": len(commands), "expected_command_count": len(EXPECTED_COMMANDS), "missing_commands": sorted(EXPECTED_COMMANDS - commands), "unexpected_commands": sorted(commands - EXPECTED_COMMANDS)}
    return {"method": method, "ok": False, "error_code": None}


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
            except (httpx.HTTPError, ValueError) as exc:
                print({"method": method, "error_type": type(exc).__name__})
                raise SystemExit(1) from None


if __name__ == "__main__":
    asyncio.run(main())
