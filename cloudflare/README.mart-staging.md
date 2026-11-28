# MART Telegram staging webhook

Research-branch-only Cloudflare Worker implementing the Python Telegram menu and inline callback presentation. No Python business engine, publishing, research provider, cron or webhook registration is included.

## Verify offline

Run `node --test cloudflare/test*.mjs` from repository root with Node 24. The test suite never calls Telegram.

## Configuration

The Wrangler file is `cloudflare/wrangler.mart-staging.toml`. Run Wrangler with `--config cloudflare/wrangler.mart-staging.toml` from the repository root, with the entrypoint relative to its config directory. An unset delivery flag or the value `false` enables preview. The checked-in staging configuration explicitly sets the flag to `true`.

Set `TELEGRAM_WEBHOOK_SECRET` as a Worker secret for authenticated preview. Do not copy secrets into source or TOML. The `TELEGRAM_BOT_TOKEN` Worker secret is only needed for future explicitly approved delivery tests. Rotate any token previously exposed in chat.

## Safety

Do not register a live Telegram webhook against this Worker while preview-only. Telegram will consider its HTTP 200 response delivered, so updates would be consumed without a chat reply. Use synthetic HTTP requests to test preview. Deploying, enabling delivery and registering a webhook are distinct, unperformed operations requiring authorization. Do not replace the existing production webhook. No billing or production changes are required for offline validation.

## Reply recovery

Delivery of every rendered reply uses the START_JOBS SQLite Durable Object binding. Each bot/update pair has one stored menu intent. Concurrent deliveries share the active send. A completed job retains only its completion marker. A Telegram HTTP 429 leaves the job pending for webhook redelivery. If the process stops after reserving the send, or loses its receipt, the job remains in sending and returns 503 on replay. Investigate the receipt before attempting a manual resend. Webhook redeliveries during a Telegram retry_after interval make no outbound send. Callback acknowledgement is best effort and an expired callback can still receive its guide. Existing pending /start payloads remain readable.
