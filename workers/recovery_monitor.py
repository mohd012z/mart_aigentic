"""Repair stale terminal leases and summarize D1 queue health."""
import time
from workers.durable_consumer import MAX_ATTEMPTS

async def reap_exhausted(db, now=None):
    now=int(time.time()) if now is None else now
    return await db.query("""UPDATE telegram_updates SET status='dead',
      lease_until=NULL,worker_id=NULL,last_error_code='lease_exhausted',
      updated_at=?1 WHERE status='processing' AND lease_until<=?1
      AND attempts>=?2 RETURNING update_id""",(now,MAX_ATTEMPTS))

async def health(db):
    return await db.query("""SELECT status,COUNT(*) AS total FROM telegram_updates
      GROUP BY status ORDER BY status""")
