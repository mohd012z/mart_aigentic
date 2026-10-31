"""D1-backed durable Telegram update consumer. No automatic deployment or polling."""
import asyncio
import json
import os
import time
import uuid
import httpx

MAX_ATTEMPTS = 5
LEASE_SECONDS = 120

class D1:
    def __init__(self, account_id, database_id, api_token):
        if not all((account_id, database_id, api_token)):
            raise ValueError("D1 credentials required")
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
        self.token = api_token

    async def query(self, sql, params=()):
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.url, headers={"Authorization": f"Bearer {self.token}"},
                json={"sql": sql, "params": list(params)})
            response.raise_for_status()
            body = response.json()
        if not body.get("success") or not body.get("result") or not body["result"][0].get("success"):
            raise RuntimeError("D1 query failed")
        return body["result"][0].get("results", [])

async def claim(db, now=None, worker_id=None):
    now = int(time.time()) if now is None else now
    worker_id = worker_id or uuid.uuid4().hex
    rows = await db.query("""
      UPDATE telegram_updates SET status='processing', attempts=attempts+1,
        lease_until=?1, worker_id=?2, updated_at=?3
      WHERE update_id=(
        SELECT update_id FROM telegram_updates
        WHERE attempts<?4 AND ((status='pending' AND next_attempt_at<=?3)
           OR (status='processing' AND lease_until<=?3))
        ORDER BY created_at,update_id LIMIT 1
      )
      AND attempts<?4
      RETURNING update_id,payload,attempts,worker_id
    """, (now + LEASE_SECONDS, worker_id, now, MAX_ATTEMPTS))
    return rows[0] if rows else None

async def complete(db, row, now=None):
    now = int(time.time()) if now is None else now
    return await db.query("""UPDATE telegram_updates SET status='completed',
      lease_until=NULL,worker_id=NULL,updated_at=?3
      WHERE update_id=?1 AND worker_id=?2 AND status='processing' AND lease_until>=?3
      RETURNING update_id""", (row["update_id"], row["worker_id"], now))

async def fail(db, row, code="processing_failed", now=None):
    now = int(time.time()) if now is None else now
    attempts = int(row["attempts"])
    terminal = attempts >= MAX_ATTEMPTS
    delay = min(3600, 2 ** min(attempts, 10))
    return await db.query("""UPDATE telegram_updates SET status=?3,
      next_attempt_at=?4,lease_until=NULL,worker_id=NULL,last_error_code=?5,
      updated_at=?6 WHERE update_id=?1 AND worker_id=?2 AND status='processing' AND lease_until>=?6
      RETURNING update_id""", (row["update_id"], row["worker_id"],
          "dead" if terminal else "pending", now + delay, code[:64], now))

async def run_once(db, handler):
    row = await claim(db)
    if row is None:
        return "idle"
    try:
        update = json.loads(row["payload"])
        await handler(update)
    except Exception:
        await fail(db, row)
        return "retry"
    if not await complete(db, row):
        raise RuntimeError("Lease ownership lost; processing outcome ambiguous")
    return "completed"

async def main():
    db = D1(os.environ["CF_ACCOUNT_ID"], os.environ["CF_D1_DATABASE_ID"], os.environ["CF_D1_API_TOKEN"])
    # Deliberately no live handler: use a tested delivery adapter before activation.
    raise SystemExit("Consumer transport configured; live handler integration requires approval")

if __name__ == "__main__":
    asyncio.run(main())
