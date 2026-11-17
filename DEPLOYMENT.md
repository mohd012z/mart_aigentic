# MART V5 deployment (review branch)

This application requires a continuously running HTTPS FastAPI web process and a separate long-running worker process **sharing the same persistent SQLite database file**.

Web: `uvicorn app:app --host 0.0.0.0 --port 8000`
Worker: `python campaign_worker.py`

Required environment:
- `TELEGRAM_BOT_TOKEN`: bot credential (secret)
- `TELEGRAM_WEBHOOK_SECRET`: random webhook header secret
- `BRAVE_SEARCH_API_KEY`: search API credential
- `MART_CAMPAIGN_DB`: absolute path on a persistent shared disk, e.g. `/data/mart_campaigns.sqlite3`

Set Telegram webhook to `https://YOUR_HOST/telegram/webhook` with the `secret_token` header configured through Telegram Bot API `setWebhook`. Register menu commands separately with `python -m scripts.register_telegram_menu`.

**Do not deploy web and worker as separate containers with independent ephemeral SQLite files.** For multi-instance or serverless hosting, replace SQLite with a shared transactional database such as PostgreSQL first.

The worker retries failed research up to three times and sends completed drafts to Telegram. It does not publish to Shopee, TikTok or paid ad networks. The current implementation has a single-worker assumption; Telegram send plus SQLite acknowledgment is not exactly-once, so a crash between the two may cause a duplicate notification. Webhook update deduplication also needs transactional inbox/outbox hardening before high-volume production.

Run `python -m unittest discover -s tests -v` before deployment. No secrets belong in Git.
