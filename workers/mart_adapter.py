"""Offline ASGI adapter for existing MART webhook; no live Telegram API calls unless configured."""
import httpx
from app import app

async def deliver_update(update, *, secret, app_instance=None):
    """Dispatch an already authenticated D1 inbox item to existing MART handler.

    The adapter uses an in-process ASGI transport, preserving the existing command
    routing. Inject a mocked app in tests. A successful 2xx means MART accepted
    the update, not necessarily that Telegram received a unique reply.
    """
    if not secret:
        raise ValueError("TELEGRAM_WEBHOOK_SECRET required")
    transport = httpx.ASGITransport(app=app_instance or app, raise_app_exceptions=True)
    async with httpx.AsyncClient(transport=transport,base_url="http://mart.internal") as client:
        response=await client.post("/telegram/webhook",json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token":secret})
        response.raise_for_status()
        result=response.json()
        if not result.get("ok"):
            raise RuntimeError("MART handler did not acknowledge update")
        return result
