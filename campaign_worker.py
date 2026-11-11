"""Run one queued campaign. Publishing is deliberately disabled."""
import asyncio
from campaigns import claim, finish
from mart_engine import research
from drafts import create_draft

def _build_output(topic, evidence):
    ad = create_draft("ads", topic)
    social = create_draft("social", topic)
    video = create_draft("video", topic)
    parts = [f"CAMPAIGN DRAFT: {topic}\n\nEVIDENCE\n{evidence[:1500]}\n\n"]
    parts.append("AD DRAFT\n" + ad + "\n\n")
    parts.append("SOCIAL DRAFT\n" + social + "\n\n")
    parts.append("VIDEO DRAFT\n" + video + "\n\n")
    parts.append("Review factual claims, copyright, disclosures and platform "
                 "rules. Nothing published.")
    return "".join(parts)[:3900]

async def run_once():
    job = claim()
    if not job:
        return False
    cid, chat, topic = job
    try:
        evidence = await research(topic)
        offline = evidence.startswith(("Research provider not configured", "Research unavailable"))
        if offline:
            evidence = ("Research provider not configured at run time — offline draft. "
                        "Verify all factual claims against live sources before publishing.")
        finish(cid, _build_output(topic, evidence))
        return True
    except Exception as e:
        finish(cid, type(e).__name__ + ": " + str(e), False)
        return False

if __name__ == "__main__":
    asyncio.run(run_once())
