"""Manually register and verify MART commands; no other Bot API methods."""
import asyncio
import os
import re
import sys

import httpx
from telegram_ui import COMMANDS

async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise RuntimeError("Missing or malformed TELEGRAM_BOT_TOKEN")
    expected = len(COMMANDS)
    if expected != len({c["command"] for c in COMMANDS}):
        raise RuntimeError("Commands are not distinct")
    for item in COMMANDS:
        if not re.fullmatch(r"[a-z0-9_]{1,32}", item["command"]):
            raise RuntimeError("Invalid command")
        if not 1 <= len(item["description"]) <= 256:
            raise RuntimeError("Invalid command description")
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        base = "https://api.telegram.org/bot" + token + "/"
        # Do not log request URLs or exceptions: Bot API URLs contain the token.
        try:
            response = await client.post(base + "setMyCommands", json={"commands": COMMANDS})
            if response.status_code != 200 or response.json().get("ok") is not True or response.json().get("result") is not True:
                raise RuntimeError("Telegram command registration rejected")
            verification = await client.post(base + "getMyCommands")
            if verification.status_code != 200 or verification.json().get("ok") is not True:
                raise RuntimeError("Telegram command verification rejected")
            actual = verification.json().get("result")
        except (httpx.HTTPError, ValueError):
            raise RuntimeError("Telegram registration/verification request failed") from None
    if actual != COMMANDS:
        raise RuntimeError("Registered command list does not match all expected commands")
    print(f"PASS: Telegram confirmed exact parity for {expected} MART commands.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
