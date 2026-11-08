"""Synchronize secrets only to the isolated MART staging Worker.

No webhook registration, live Telegram requests, deployment or production changes.
"""
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request

ACCOUNT_ID = "6f98e71e31e6948932159d11ca267abb"
WORKER = "mart-telegram-research-staging"
ENDPOINT = (
    f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}"
    f"/workers/scripts/{WORKER}/secrets"
)


def main():
    cloudflare = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    telegram = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not cloudflare or not telegram:
        print("BLOCKED: CLOUDFLARE_API_TOKEN or TELEGRAM_BOT_TOKEN unavailable")
        return 2
    prefix, separator, suffix = telegram.partition(":")
    if not (separator and prefix.isdigit() and len(suffix) >= 30):
        print("BLOCKED: malformed Telegram token")
        return 2

    # A dedicated 64-character webhook secret derived from the rotated bot token.
    # Neither the token nor derived secret is written to logs or repository files.
    webhook_secret = hmac.new(
        telegram.encode("utf-8"),
        b"mart-telegram-research-staging:webhook-secret:v1",
        hashlib.sha256,
    ).hexdigest()

    for name, value in (
        ("TELEGRAM_BOT_TOKEN", telegram),
        ("TELEGRAM_WEBHOOK_SECRET", webhook_secret),
    ):
        request = urllib.request.Request(
            ENDPOINT,
            data=json.dumps({"name": name, "text": value, "type": "secret_text"}).encode(),
            headers={
                "Authorization": "Bearer " + cloudflare,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.load(response)
            if result.get("success") is not True:
                print(f"FAILED: staging secret {name} was rejected")
                return 1
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            print(f"FAILED: staging secret {name} could not be synchronized")
            return 1
        print(f"PASS: staging secret {name} synchronized")
    print("PASS: staging-only secret sync; no Telegram messages or webhook registration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
