# MART Telegram durable ingress (NOT DEPLOYED)

Worker validates Telegram secret header, accepts POST /telegram/webhook, and atomically inserts update_id into Cloudflare D1. Repeated updates are acknowledged without duplicate inserts. Storage errors return HTTP 503 so Telegram can retry. It never calls Telegram setWebhook, never executes research, and never publishes content.

## Deployment approval gates
1. Obtain sanitized getWebhookInfo values; identify the existing webhook and its hosting owner.
2. Verify Worker tests and D1 schema on a disposable development database.
3. Configure a dedicated development D1 binding MART_DB and Worker secret TELEGRAM_WEBHOOK_SECRET.
4. Implement and test a separate authenticated Python consumer; Worker alone does not reply to messages.
5. Verify bounded leases, retry backoff, dead-letter handling, monitoring, and safe duplicate sends.
6. Obtain explicit approval before any live webhook switch or deployment.

## Migration
Existing campaigns.py SQLite is process-local. Do not copy its update IDs blindly to D1. Freeze live intake only during an approved cutover, export a consistent SQLite snapshot, import campaigns/sessions and processed update IDs with idempotent upserts, validate row counts and foreign associations, then cut over only after worker and consumer are healthy. Preserve a rollback snapshot. Keep business campaign storage separate from webhook inbox if the migration is staged.

## Consumer algorithm (design, not implemented)
Claim with an atomic conditional UPDATE of due pending rows or expired processing leases; increment attempts and set lease_until. Process outside transaction. On success mark completed only for the matching worker_id. On failure retry with exponential backoff and jitter, capped at 5 attempts, then mark dead. Use an outgoing message idempotency/outbox key and audit Telegram send ambiguity; Telegram sendMessage does not offer a general idempotency key, so exactly-once external delivery cannot be guaranteed.
