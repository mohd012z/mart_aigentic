# MART Global Integration Architecture — 2026-10-31

## Evidence and constraints
- Postiz provides a reference for platform adapters and background scheduling; its full stack is heavier than a minimal Telegram bot.
- Threads has distinct OAuth scopes and authorization; do not reuse Facebook tokens.
- TikTok Content Posting API requires authorized publish scope and user consent. Unaudited clients face private visibility restrictions.
- Shopee Seller Centre login is not a Partner ID/Key; official API access is pending.
- Existing MART app.py runs research inline in Telegram webhook; campaigns.py uses local SQLite deduplication.

## Architecture decision records
ADR-001: Keep main/live bot unchanged. Integrate behind a disabled feature flag.
ADR-002: One platform adapter per provider, with explicit capabilities: draft, read, publish, metrics.
ADR-003: No publish without valid OAuth permissions, owner approval, idempotency key, and current platform policy validation.
ADR-004: Durable PostgreSQL queue for multi-worker production; SQLite is acceptable only for single-process development with persistent storage.
ADR-005: Persist immutable approval records and separate user-facing job status from provider-confirmed publication.
ADR-006: Prefer webhook quick ACK and durable queue to in-process background tasks.
ADR-007: Keep Shopee seller and Shopee affiliate authorization separate.
ADR-008: LLM outputs are proposals. Product claims, prices, inventory and promotion terms require verified inputs.
ADR-009: Protect webhook endpoint with Telegram secret header plus user allowlist and private-chat checks.
ADR-010: Store OAuth secrets in server-side encrypted storage; use PKCE/state where supported, short token lifetimes, and rotation.

## Planned queue states
queued -> researching -> drafted -> review -> approved -> scheduled -> submitting -> processing -> published
Failure paths: rejected, retry_wait, failed, canceled.
A retry must never blindly repeat a non-idempotent publish request. Reconcile provider status first.

## Minimum test gates before enabling feature
- Webhook secret and Telegram sender authorization
- Unauthorized users cannot see imported seller data
- Duplicated Telegram update does not duplicate jobs
- Owner-only approval and campaign version locking
- Queue restart and recovery; no lost tasks
- OAuth state/nonce validation and token redaction
- CSV limits, formula injection-safe exports, encoding and malformed row handling
- Per-platform payload constraints and media checks
- Simulated API 401/403/429/5xx, backoff, expiry and duplicate publish prevention
- Provider-confirmed publish receipt and audit trace
- Existing research and campaign command regression tests

## Delivery stages
M1: Telegram /commerce UI, auth gate and draft previews
M2: Persistent job queue and approvals
M3: Configurable hosted LLM adapter with structured outputs and factual validation
M4: Official Meta OAuth and read-only account discovery
M5: TikTok publishing adapter after permission/audit
M6: Shopee Seller API adapter after partner approval
M7: Scheduling, analytics and observability

No platform integration is currently authenticated. No live posting is implemented.
