"""Deterministic marketing content generators for MART.

Each generator takes a topic and returns a structured, topic-specific draft that a
human can verify before publishing. They are intentionally provider-free (no LLM,
no network) so they are fast, offline-testable, and never present invented numbers
as data. When an AI gateway is wired later (V6/V7 PRs), these become the fallback.
"""
import re

_MAX = 3900


def _topic(topic):
    t = re.sub(r"\s+", " ", (topic or "")).strip()
    return t[:250] or "your product"


def _first_sentence(topic):
    t = _topic(topic)
    for stop in (".", " —", " -"):
        idx = t.find(stop)
        if 0 < idx <= 80:
            return t[:idx].strip()
    return t[:80].strip()


# ---------------------------------------------------------------- marketing ---
def marketing_plan(topic):
    t = _topic(topic)
    name = _first_sentence(t)
    L = []
    L.append(f"📣 MARKETING PLAN — {t}\n")
    L.append("1) OBJECTIVE\n"
             f"• Define one measurable 30-day goal for {name} (e.g. qualified leads, "
             "pilot sign-ups, or a first paid sale). Pick ONE — not several.\n")
    L.append("2) AUDIENCE & POSITIONING\n"
             "• Target one primary segment: describe who they are, the job they're "
             f"trying to do, and the trigger that makes them search for {name}.\n"
             "• Position against the nearest substitute, not 'everyone'. "
             "State the one reason to switch.\n")
    L.append("3) CHANNELS (pick 1-2 to start)\n"
             "• High-intent search / ads — best if demand already exists for "
             f"{name}; test a small budget, measure cost per result.\n"
             "• Social (organic + targeted) — best for awareness and retargeting; "
             "slower, compounds over time.\n"
             "• Direct / partnership (email, affiliates, communities) — best when "
             "you can reach the audience through an existing trusted channel.\n")
    L.append("4) FUNNEL\n"
             "Awareness → Interest → Decision → Action. For each step decide what "
             f"{name} shows the user and what the next click is.\n")
    L.append("5) BUDGET (test phase)\n"
             "• Split a small test budget ~50/30/20 across your top 2 channels + "
             "creative testing. Reallocate weekly to the best cost-per-result.\n")
    L.append("6) KPIs TO TRACK\n"
             "• Cost per result, conversion rate, click-through rate, and one "
             "revenue/retention metric. Review weekly; cut what doesn't move.\n")
    L.append("7) 30-DAY CALENDAR\n"
             "• W1: lock offer + message, build 2 channels, launch test.\n"
             "• W2: first data, kill weak creative, add retargeting.\n"
             "• W3: scale what works, test 1 new angle.\n"
             "• W4: review KPIs, set the next 30-day goal.\n")
    L.append("🔒 Draft — verify claims, pricing and targeting before publishing. "
             "No spend has been made.")
    return "\n".join(L)[:_MAX]


# --------------------------------------------------------------------- ads ---
def ads_draft(topic):
    t = _topic(topic)
    name = _first_sentence(t)
    L = []
    L.append(f"🎯 AD COPY — {t}\n")
    L.append("HEADLINES (pick one)\n"
             f"• {name} — without the guesswork\n"
             f"• Why people are switching to {name}\n"
             f"• The smarter way to handle {name}\n")
    L.append("PLATFORM VARIANTS\n\n"
             "▸ Meta / Facebook (primary text)\n"
             f"Struggling with {name}? Get a clear, low-risk way to start — "
             "no fluff, just what works. See how in 30 seconds.\n"
             "CTA: Learn More\n\n"
             "▸ Google Search (3 headlines ≤30 chars + description ≤90)\n"
             f"H1: {name[:29]}\n"
             "H2: Compare Options Fast\n"
             "H3: Low-Risk Getting Started\n"
             f"Desc: See how {name} works, what it costs, and who it's for. "
             "Start your research here.\n\n"
             "▸ TikTok / Shorts (spoken hook → CTA)\n"
             f"Hook: 'Stop overthinking {name}.' → 3 quick points → "
             "'Follow for the full breakdown.'\n")
    L.append("A/B SUGGESTION\n"
             "Test a benefit-led vs. curiosity-led headline against identical body "
             "copy for 3-5 days; keep the one with lower cost per result.\n")
    L.append("🔒 Verify every claim and price before running. Add a disclosure if "
             "it's an affiliate link.")
    return "\n".join(L)[:_MAX]


# ------------------------------------------------------------------ social ---
def social_draft(topic):
    t = _topic(topic)
    name = _first_sentence(t)
    tag = re.sub(r"[^a-z0-9]", "", name.lower())[:16] or "research"
    L = []
    L.append(f"📱 SOCIAL CONTENT — {t}\n")
    L.append("7-DAY CALENDAR (one post/day)\n"
             f"• D1 Hook: the problem {name} solves\n"
             "• D2 Proof: a quick result or comparison\n"
             "• D3 Education: one myth vs. the truth\n"
             f"• D4 Behind-the-scenes: how {name} works\n"
             "• D5 FAQ: the #1 objection, answered\n"
             "• D6 Tip: a fast, actionable win\n"
             "• D7 CTA: how to get started\n")
    L.append("READY-TO-POST CAPTIONS (EN)\n\n"
             f"1) Hook: 'Most people get {name} wrong.'\n"
             "Body: Here's what actually matters → [one point]. Save this for later.\n"
             f"#research #{tag}\n\n"
             f"2) Hook: 'Before you start {name}, read this.'\n"
             "Body: 3 things to check first → [list]. Which one surprised you? 👇\n\n"
             f"3) Hook: 'The 60-second version of {name}.'\n"
             "Body: [point] + [point] + how to start. Share with someone who's looking.\n")
    L.append("MALAY (BM) VERSION — for the MY market\n\n"
             f"1) 'Ramai salah faham pasal {name}.\n"
             "Nak tahu yang betul? Simpan post ni. 👇'\n\n"
             f"2) 'Sebelum mula {name}, semak 3 benda ni dulu.\n"
             "Sila kongsi kepada yang perlukan.'\n")
    L.append("ENGAGEMENT: end each post with a one-line question. Disclose "
             "affiliate relationships where they apply.\n")
    L.append("🔒 Draft — verify facts before posting.")
    return "\n".join(L)[:_MAX]


# ------------------------------------------------------------------ video ---
def video_draft(topic):
    t = _topic(topic)
    name = _first_sentence(t)
    L = []
    L.append(f"🎬 VIDEO SCRIPT — {t}\n")
    L.append("30-SECOND CUT\n"
             f"[0-3s]  HOOK (on-screen + VO): 'Stop wasting time on {name}.'\n"
             f"[3-10s] PROBLEM: name the #1 frustration with {name}.\n"
             f"[10-22s] VALUE: 3 fast points on how {name} actually works.\n"
             "[22-27s] PROOF: one concrete, verifiable example.\n"
             "[27-30s] CTA: 'Follow / tap the link for the full guide.'\n")
    L.append("60-SECOND CUT (adds)\n"
             "[10-22s] Expand each point with a 'before → after' framing.\n"
             "[30-45s] Objection handling: the one thing people worry about "
             f"with {name}, answered in one line.\n"
             "[45-55s] Social proof / result + on-screen caption of the key claim.\n"
             "[55-60s] Strong CTA + where to go next.\n")
    L.append("PRODUCTION NOTES\n"
             "• Vertical 9:16, on-screen text for the 3 key points (most watch muted).\n"
             f"• B-roll: real footage of {name}, not stock clichés. Licensed media only.\n"
             "• Export with captions (SRT): one short cut + one long cut.\n")
    L.append("🔒 Draft — verify every on-screen claim before filming.")
    return "\n".join(L)[:_MAX]


_GENERATORS = {
    "marketing": marketing_plan,
    "ads": ads_draft,
    "social": social_draft,
    "video": video_draft,
}


def create_draft(kind, topic):
    gen = _GENERATORS.get(kind)
    if not gen:
        return (f"{kind.upper()} — {topic}\n\n"
                "Research affiliate products, disclose partnerships, and verify "
                "product claims before publishing.")
    return gen(topic)
