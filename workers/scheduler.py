"""Bounded one-shot queue maintenance; no perpetual process or live deployment."""
import asyncio
from workers.durable_consumer import run_once
from workers.outbox_sender import deliver_once,quarantine_expired
from workers.recovery_monitor import reap_exhausted,health

async def cycle(db,handler,token,*,max_updates=10,max_sends=10):
    if not 0<=max_updates<=100 or not 0<=max_sends<=100:
        raise ValueError('Invalid cycle bounds')
    await reap_exhausted(db)
    await quarantine_expired(db)
    results={'updates':[],'sends':[]}
    for _ in range(max_updates):
        state=await run_once(db,handler)
        if state=='idle':break
        results['updates'].append(state)
    for _ in range(max_sends):
        state=await deliver_once(db,token)
        if state=='idle':break
        results['sends'].append(state)
    results['health']=await health(db)
    return results
