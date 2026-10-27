# MART Agentic Research & Marketing Engine

Telegram target: @mart_aigenticbot.

## Current scope
Webhook-based Telegram research commands, Brave Search evidence retrieval, URL deduplication, transparent heuristic scoring and Python tests. This is a foundation, not an autonomous publishing system.

## Required environment
- TELEGRAM_BOT_TOKEN (secret)
- TELEGRAM_WEBHOOK_SECRET (random secret used in Telegram setWebhook secret_token)
- BRAVE_SEARCH_API_KEY (required for live research)

Install: `pip install -r requirements.txt`
Run: `uvicorn app:app --host 0.0.0.0 --port 8000`
Test: `python -m unittest discover -s tests -v`

Deploy on an always-on HTTPS host. Register the webhook with Telegram using `setWebhook`, URL `https://YOUR_HOST/telegram/webhook`, and the matching `secret_token`. Do not commit tokens. GitHub Actions is used for CI, not as a Telegram polling loop.

## Limitations
The current request handler performs synchronous research before replying, so longer requests can exceed Telegram's webhook deadline. Production upgrade: durable queue, immediate acknowledgment, async worker, idempotency by update_id, retries, audit logs, source freshness checks, and rate limiting. No autonomous publishing is enabled.
