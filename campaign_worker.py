"""Run one queued campaign. Publishing is deliberately disabled."""
import asyncio
from campaigns import claim,finish
from mart_engine import research
async def run_once():
    job=claim()
    if not job:return False
    cid,chat,topic=job
    try:
        evidence=await research(topic)
        if evidence.startswith(("Research provider not configured","Research unavailable")):
            raise RuntimeError("Research provider unavailable")
        output=(f"CAMPAIGN DRAFT: {topic}\n\nEVIDENCE\n{evidence[:1800]}\n\n"
                f"AD: Explore {topic}. Compare features and options. CTA: Learn more.\n\n"
                f"SOCIAL: Three considerations before choosing {topic}.\n\n"
                "VIDEO: 0-3s hook, 3-15s problem, 15-30s comparison, 30-35s CTA.\n\n"
                "Review factual claims, copyright, disclosures and platform rules. Nothing published.")
        finish(cid,output)
        return True
    except Exception as e:
        finish(cid,type(e).__name__+": "+str(e),False)
        return False
if __name__=="__main__":asyncio.run(run_once())
