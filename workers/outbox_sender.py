"""Conservative D1 outbox transport: never automatically retry an ambiguous send."""
import json
import time
import uuid
import httpx

MAX_ATTEMPTS=5
LEASE_SECONDS=90

async def claim(db,now=None,owner=None):
    now=int(time.time()) if now is None else now
    owner=owner or uuid.uuid4().hex
    rows=await db.query("""
      UPDATE telegram_outbox SET state='sending',attempts=attempts+1,
      lease_until=?1,worker_id=?2,updated_at=?3
      WHERE id=(SELECT id FROM telegram_outbox
        WHERE state='pending' AND (lease_until IS NULL OR lease_until<=?3)
        AND attempts<?4 ORDER BY created_at,id LIMIT 1)
      AND state='pending' AND attempts<?4
      RETURNING id,chat_id,method,payload,attempts,worker_id
    """,(now+LEASE_SECONDS,owner,now,MAX_ATTEMPTS))
    return rows[0] if rows else None

async def transition(db,row,state,now=None,telegram_message_id=None,error=None):
    now=int(time.time()) if now is None else now
    if state not in ('sent','uncertain','dead','pending'):
        raise ValueError('Invalid outbox state')
    return await db.query("""
      UPDATE telegram_outbox SET state=?3,lease_until=NULL,worker_id=NULL,
        telegram_message_id=?4,last_error_code=?5,updated_at=?6
      WHERE id=?1 AND worker_id=?2 AND state='sending'
      RETURNING id
    """,(row['id'],row['worker_id'],state,telegram_message_id,error,now))

async def deliver_once(db,token,client=None):
    row=await claim(db)
    if row is None:return 'idle'
    own=client is None
    if own:client=httpx.AsyncClient(timeout=15)
    try:
        payload=json.loads(row['payload'])
        if row['method'] not in ('sendMessage','answerCallbackQuery'):
            await transition(db,row,'dead',error='unsupported_method')
            return 'dead'
        try:
            response=await client.post(
                f"https://api.telegram.org/bot{token}/{row['method']}",json=payload)
        except (httpx.TimeoutException,httpx.TransportError):
            await transition(db,row,'uncertain',error='transport_ambiguous')
            return 'uncertain'
        try:body=response.json()
        except ValueError:
            await transition(db,row,'uncertain',error='invalid_response')
            return 'uncertain'
        if response.status_code==200 and body.get('ok') is True:
            msg=body.get('result') or {}
            await transition(db,row,'sent',telegram_message_id=msg.get('message_id'))
            return 'sent'
        # 429 and 5xx may have ambiguous server-side effects; require reconciliation.
        if response.status_code==429 or response.status_code>=500:
            await transition(db,row,'uncertain',error='server_or_rate_limit')
            return 'uncertain'
        await transition(db,row,'dead',error='telegram_rejected')
        return 'dead'
    finally:
        if own:await client.aclose()

async def quarantine_expired(db,now=None):
    now=int(time.time()) if now is None else now
    return await db.query("""
      UPDATE telegram_outbox SET state='uncertain',worker_id=NULL,lease_until=NULL,
      last_error_code='expired_sending_lease',updated_at=?1
      WHERE state='sending' AND lease_until<=?1 RETURNING id
    """,(now,))

async def reconcile(db,record_id,decision):
    """Operator-only reconciliation: never infer non-delivery from a timeout."""
    if decision not in ('sent','dead'):raise ValueError('Manual reconciliation required')
    return await db.query("""
      UPDATE telegram_outbox SET state=?2,updated_at=?3
      WHERE id=?1 AND state='uncertain' RETURNING id
    """,(record_id,decision,int(time.time())))
