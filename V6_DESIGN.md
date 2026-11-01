# MART V6 gateway and provider registry
This release introduces a **disabled-until-configured** AI text gateway. It does not publish advertisements or connect to Shopee/TikTok.

## Configuration
- `MART_LLM_API_KEY` and `MART_LLM_MODEL` for the fixed OpenAI-compatible HTTPS endpoint.
- Optional local loopback proxy: `MART_ENABLE_LOCAL_GATEWAY=1`, `MART_LOCAL_GATEWAY_KEY`, `MART_LOCAL_MODEL`.
- Local gateway must run on the same network namespace; never expose it publicly without authentication.
- No automatic account rotation, credential harvesting, or bypass of provider limits.

## Next steps
- Add task-specific prompts with source-grounded claims and review gating.
- Add token/cost telemetry from response usage.
- Introduce per-user and per-campaign budgets and circuit breakers.
- Use a shared transactional database for distributed deployment.
- Verify CI and deployment before merge.
