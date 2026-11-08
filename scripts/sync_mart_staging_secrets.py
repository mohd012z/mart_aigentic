"""Upload MART staging Worker secrets without printing values or changing routes."""
import json
import os
import sys
import urllib.error
import urllib.request

WORKER = "mart-telegram-research-staging"
NAMES = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET")


def main():
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    telegram = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    webhook = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not token or not account or not telegram or not webhook:
        print("BLOCKED: one or more required staging credentials are absent")
        return 2
    if not (len(account) == 32 and all(c in "0123456789abcdef" for c in account.lower())):
        print("BLOCKED: invalid Cloudflare account ID")
        return 2
    if not (telegram.partition(":")[0].isdigit() and telegram.partition(":")[1] and len(telegram.partition(":")[2]) >= 30):
        print("BLOCKED: malformed Telegram token")
        return 2
    if not (8 <= len(webhook) <= 256 and all(c.isalnum() or c in "_-" for c in webhook)):
        print("BLOCKED: invalid Telegram webhook secret")
        return 2
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{WORKER}/secrets"
    for name, value in zip(NAMES, (telegram, webhook)):
        request = urllib.request.Request(
            url,
            data=json.dumps({"name": name, "text": value, "type": "secret_text"}).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.load(response)
            if result.get("success") is not True:
                print(f"FAILED: Cloudflare rejected {name} without exposing response details")
                return 1
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            print(f"FAILED: Cloudflare API request for {name}")
            return 1
        print(f"PASS: staging secret {name} uploaded")
    print("PASS: only staging secrets updated; no webhook registration or Telegram messages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
