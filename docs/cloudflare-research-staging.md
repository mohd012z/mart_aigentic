# Cloudflare MART research staging integration

The existing Telegram webhook stays with MART's Python ASGI service. No Telegram `setWebhook` change is required.

Cloudflare Worker: `mart-research-staging`
D1 database: `mart-research-staging-db`

## Secure configuration

In Cloudflare Worker Settings → Variables and Secrets, add encrypted secrets:
- `MART_INTERNAL_KEY`: a long, randomly generated secret shared with the MART Python host.
- `BRAVE_SEARCH_API_KEY`: your own authorized Brave Search API key.
- `TELEGRAM_BOT_TOKEN`: the existing MART bot's token, as a secret; never commit or paste it in a chat.

On the MART Python host, configure `MART_RESEARCH_WORKER_URL` (the actual HTTPS Worker URL) and `MART_INTERNAL_KEY` (the matching secret). Without both, MART continues its previous research path.

Enable a Cloudflare Worker HTTPS route only after validating the secret and host. Configure an appropriate Cron Trigger for the Worker scheduled handler. Do not register a second Telegram webhook.

## Processing semantics

POST `/enqueue` uses Bearer authentication and a deterministic request ID. D1 deduplicates the ID. The scheduled handler searches Brave, persists results, then attempts Telegram delivery.

**Limitations:** Telegram sends and D1 updates are not atomic. If the Worker crashes after Telegram accepts a message but before D1 records `sent`, a retry can duplicate the message. A crashed `running` job can remain stuck because no lease recovery exists yet. Do not claim exactly-once delivery or production readiness. The current worker requires an explicit trigger and configured credentials. Live Telegram and Brave requests have not been verified.

## Verification

Run `python -m unittest discover -s tests -v` and confirm all tests pass before deploying. Verify a real research request, persisted job, Telegram delivery and restart recovery in staging. Preserve main and existing webhook until verified.
