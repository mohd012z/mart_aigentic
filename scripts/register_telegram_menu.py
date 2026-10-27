"""Run once after configuring TELEGRAM_BOT_TOKEN to register the command menu."""
import asyncio
import os
import httpx
from telegram_ui import COMMANDS

async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN must be configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/setMyCommands",
            json={"commands": COMMANDS},
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise SystemExit("Telegram rejected the command registration")
    print("Telegram command menu registered.")

if __name__ == "__main__":
    asyncio.run(main())
