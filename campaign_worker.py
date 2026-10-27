"""Long-running campaign worker with bounded retries and Telegram notifications."""
import asyncio
import logging
import os
import sqlite3
import time
from contextlib import closing
import httpx
import campaigns
from mart_engine import research
from ai_gateway import generate, GatewayError
from provider_registry import configured

log=logging.getLogger(__name__)
POLL_SECONDS=float(os.getenv("MART_WORKER_POLL_SECONDS","5"))
MAX_ATTEMPTS=3

def migrate():
    with closing(campaigns.conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        cols={r[1] for r in c.execute("PRAGMA table_info(campaigns)")}
        for col,typ in (("attempts","INTEGER NOT NULL DEFAULT 0"),("available_at","INTEGER NOT NULL DEFAULT 0"),("lease_until","INTEGER NOT NULL DEFAULT 0"),("notified","INTEGER NOT NULL DEFAULT 0")):
            if col not in cols:c.execute(f"ALTER TABLE campaigns ADD COLUMN {col} {typ}")
        c.commit()

def claim():
    migrate()
    now=int(time.time())
    with campaigns.conn() as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("""SELECT id,chat,topic,attempts FROM campaigns
            WHERE (status='queued' AND available_at<=?)
            OR (status='running' AND lease_until<=?)
            ORDER BY rowid LIMIT 1""",(now,now)).fetchone()
        if row:
            c.execute("""UPDATE campaigns SET status='running',attempts=attempts+1,
                lease_until=? WHERE id=?""",(now+90,row[0]))
        c.commit()
        return row

def complete(cid,output,success=True,retry=False):
    with campaigns.conn() as c:
        if retry:
            c.execute("""UPDATE campaigns SET status='queued',available_at=?,
                lease_until=0,output=? WHERE id=?""",(int(time.time())+30,output,cid))
        else:
            c.execute("""UPDATE campaigns SET status=?,lease_until=0,output=? WHERE id=?""",
                      ("review" if success else "failed",output,cid))
        c.commit()

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
    cid,chat,topic,attempts=job
    try:
        evidence=await research(topic)
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
                generated = await generate(prompt)
                output = ("AI CAMPAIGN DRAFT: " + topic + "\n\n" + generated[:3200]
                          + "\n\nHuman review required. Nothing published.")
            except GatewayError:
                log.exception("AI generation failed; using deterministic draft")
        complete(cid,output)
    except Exception as exc:
        log.exception("Campaign %s failed",cid)
        complete(cid,f"{type(exc).__name__}: {str(exc)[:180]}",False,retry=attempts+1<MAX_ATTEMPTS)
    await deliver_pending()
    return True

async def serve():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            await run_once()
            await deliver_pending()
        except Exception:
            log.exception("Worker cycle failed")
        await asyncio.sleep(max(POLL_SECONDS,1))

if __name__=="__main__":
    asyncio.run(serve())
