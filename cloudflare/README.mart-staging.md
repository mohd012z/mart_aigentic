# MART Telegram staging webhook

Research-branch-only Cloudflare Worker implementing the Python Telegram menu and inline callback presentation. No Python business engine, database, publishing, research provider, cron or webhook registration is included.

## Verify offline

Run `node --test cloudflare/test-mart-staging.mjs` from repository root. The test suite never calls Telegram.

## Configuration

The Wrangler file is `cloudflare/wrangler.mart-staging.toml`. Run Wrangler with `--config cloudflare/wrangler.mart-staging.toml` from the repository root, with the entrypoint relative to its config directory. The default `STAGING_ENABLE_DELIVERY=false` means authenticated requests produce preview JSON only, without Telegram API calls.

Set `TELEGRAM_WEBHOOK_SECRET` as a Worker secret for authenticated preview. Do not copy secrets into source or TOML. The `TELEGRAM_BOT_TOKEN` Worker secret is only needed for future explicitly approved delivery tests. Rotate any token previously exposed in chat.

## Safety

Do not register a live Telegram webhook against this Worker while preview-only. Telegram will consider its HTTP 200 response delivered, so updates would be consumed without a chat reply. Use synthetic HTTP requests to test preview. Deploying, enabling delivery and registering a webhook are distinct, unperformed operations requiring authorization. Do not replace the existing production webhook. No billing or production changes are required for offline validation.
