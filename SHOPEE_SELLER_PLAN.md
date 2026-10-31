# Shopee Seller AI Agent — isolated implementation plan

## Current access
Seller Centre login only. No Partner ID, Partner Key, shop authorization, or live Shopee API integration is available.

## Stage 1 (implemented in seller_agent.py)
- Read-only UTF-8 CSV product import parser
- Bounded input and row count
- Product count, inventory units, low-stock identification and list-price inventory valuation
- Rule-based listing advice requiring seller review
- No credentials, no network requests, no auto-publication

## Next stages (not implemented)
1. Add Telegram /seller menu, private-chat allowlist and safe document upload.
2. Use durable storage and asynchronous job processing; do not hold webhook responses open for long work.
3. Request official Shopee Open Platform developer access and confirm Malaysia permissions.
4. Implement official seller authorization callback, state/nonce validation, signed requests and encrypted token storage.
5. Add authorized read-only product/order synchronization with retries and API rate limits.
6. Add an optional hosted LLM for grounded listing drafts with explicit approval.
7. Test webhook retries, data isolation, malformed CSV, auth failures and credential redaction.

## Safety
Never collect Seller Centre password or OTP. Do not automate browser login, scrape private seller pages or claim live data from CSV. Do not auto-change stock, prices, orders, advertising spend or listings.
