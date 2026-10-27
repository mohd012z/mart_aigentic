"""Long-running campaign worker with bounded retries and Telegram notifications."""
import asyncio
import logging
import os
import sqlite3
import time
import uuid
from contextlib import closing
import httpx
import campaigns
from mart_engine import research
from ai_gateway import generate, GatewayError
from provider_registry import configured

log=logging.getLogger(__name__)
POLL_SECONDS=float(os.getenv("MART_WORKER_POLL_SECONDS","5"))
MAX_ATTEMPTS=3
LEASE_SECONDS=90
HEARTBEAT_SECONDS=20
JOB_TIMEOUT_SECONDS=300

def migrate():
    with closing(campaigns.conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        cols={r[1] for r in c.execute("PRAGMA table_info(campaigns)")}
        for col,typ in (("attempts","INTEGER NOT NULL DEFAULT 0"),("available_at","INTEGER NOT NULL DEFAULT 0"),("lease_until","INTEGER NOT NULL DEFAULT 0"),("notified","INTEGER NOT NULL DEFAULT 0"),("lease_owner","TEXT NOT NULL DEFAULT ''")):
            if col not in cols:c.execute(f"ALTER TABLE campaigns ADD COLUMN {col} {typ}")
        c.commit()

def claim():
    migrate()
    now=int(time.time())
    with closing(campaigns.conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("""SELECT id,chat,topic,attempts FROM campaigns
            WHERE attempts<? AND ((status='queued' AND available_at<=?)
            OR (status='running' AND lease_until<=?))
            ORDER BY rowid LIMIT 1""",(MAX_ATTEMPTS,now,now)).fetchone()
        if row:
            owner=uuid.uuid4().hex
            c.execute("""UPDATE campaigns SET status='running',attempts=attempts+1,
                lease_until=?,lease_owner=? WHERE id=?""",(now+LEASE_SECONDS,owner,row[0]))
            row=(*row,owner)
        c.commit()
        return row

def complete(cid,output,success=True,retry=False,owner=None):
    if not owner:
        raise ValueError("A valid lease owner is required")
    with closing(campaigns.conn()) as c:
        if retry:
            cursor=c.execute("""UPDATE campaigns SET status='queued',available_at=?,
                lease_until=0,lease_owner='',output=? WHERE id=? AND status='running'
                AND lease_owner=?""",(int(time.time())+30,output,cid,owner))
        else:
            cursor=c.execute("""UPDATE campaigns SET status=?,lease_until=0,
                lease_owner='',output=? WHERE id=? AND status='running'
                AND lease_owner=?""",("review" if success else "failed",output,cid,owner))
        c.commit()
        return cursor.rowcount==1

def renew_lease(cid,owner):
    """Renew only the active owner's lease. Stale workers cannot renew."""
    now=int(time.time())
    with closing(campaigns.conn()) as c:
        cursor=c.execute("""UPDATE campaigns SET lease_until=?
            WHERE id=? AND status='running' AND lease_owner=?
            AND lease_until>?""",(now+LEASE_SECONDS,cid,owner,now))
        c.commit()
        return cursor.rowcount==1

async def lease_heartbeat(cid,owner,stop):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(),timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            if not renew_lease(cid,owner):
                log.warning("Lost lease for campaign %s",cid)
                stop.set()
                return

async def notify(chat,text):
    token=os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:raise RuntimeError("Telegram token missing")
    async with httpx.AsyncClient(timeout=15) as client:
        response=await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id":chat,"text":text[:4000]})
        response.raise_for_status()
        if not response.json().get("ok"):raise RuntimeError("Telegram rejected message")

async def deliver_pending():
    migrate()
    with campaigns.conn() as c:
        rows=c.execute("""SELECT id,chat,status,output FROM campaigns
            WHERE status IN ('review','failed') AND notified=0 LIMIT 10""").fetchall()
    for cid,chat,status,output in rows:
        try:
            await notify(chat,f"Campaign {cid}: {status}\n\n{output[:3500]}\n\nNo content was published.")
        except Exception:
            log.exception("Telegram delivery failed for %s",cid)
            continue
        with campaigns.conn() as c:
            c.execute("UPDATE campaigns SET notified=1 WHERE id=? AND notified=0",(cid,))
            c.commit()

async def run_once():
    job=claim()
    if not job:return False
    cid,chat,topic,attempts,owner=job
    stop=asyncio.Event()
    heartbeat=asyncio.create_task(lease_heartbeat(cid,owner,stop))
    try:
        evidence=await asyncio.wait_for(research(topic),timeout=JOB_TIMEOUT_SECONDS)
        if evidence.startswith(("Research provider not configured","Research unavailable","No verifiable sources")):
            raise RuntimeError(evidence[:150])
        output=(f"CAMPAIGN DRAFT: {topic}\n\nEVIDENCE\n{evidence[:1800]}\n\n"
                f"AD: Explore {topic}. Compare available options. CTA: Learn more.\n\n"
                f"SOCIAL: Three considerations when choosing {topic}.\n\n"
                "VIDEO: 0-3s hook; 3-15s problem; 15-30s comparison; 30-35s CTA.\n"
                "All claims, licensed assets and affiliate disclosures require review.")
        if configured("openai_compatible"):
            prompt = ("Produce a marketing draft with audience hypotheses, ad copy, a social post, "
                      "a short-video script and a list of unverified claims. Use only the supplied "
                      "evidence. Never invent prices, testimonials or commissions. Never claim "
                      "publication.\nTopic: " + topic + "\nEvidence:\n" + evidence[:4000])
            try:
                generated = await asyncio.wait_for(generate(prompt),timeout=JOB_TIMEOUT_SECONDS)
                output = ("AI CAMPAIGN DRAFT: " + topic + "\n\n" + generated[:3200]
                          + "\n\nHuman review required. Nothing published.")
            except GatewayError:
                log.exception("AI generation failed; using deterministic draft")
        if not stop.is_set() and not complete(cid,output,owner=owner):
            log.warning("Campaign %s result discarded: lease ownership changed",cid)
    except Exception as exc:
        log.exception("Campaign %s failed",cid)
        if not stop.is_set():
            complete(cid,f"{type(exc).__name__}: {str(exc)[:180]}",False,retry=attempts+1<MAX_ATTEMPTS,owner=owner)
    finally:
        stop.set()
        await heartbeat
    try:
        await deliver_pending()
    except Exception:
        log.exception('Notification delivery cycle failed after campaign completion')
    return True

async def worker_loop(worker_number):
    while True:
        try:
            await run_once()
        except Exception:
            log.exception("Worker %s cycle failed",worker_number)
        await asyncio.sleep(max(POLL_SECONDS,1))

async def notification_loop():
    while True:
        try:
            await deliver_pending()
        except Exception:
            log.exception("Notification cycle failed")
        await asyncio.sleep(max(POLL_SECONDS,1))

async def serve():
    logging.basicConfig(level=logging.INFO)
    try:
        count=int(os.getenv("MART_WORKER_COUNT","2"))
    except ValueError as exc:
        raise ValueError("MART_WORKER_COUNT must be an integer") from exc
    if not 1<=count<=4:
        raise ValueError("MART_WORKER_COUNT must be between 1 and 4")
    await asyncio.gather(*(worker_loop(i) for i in range(count)),notification_loop())

if __name__=="__main__":
    asyncio.run(serve())
