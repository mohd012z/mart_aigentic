"""MART prompt lab: complete, self-contained prompts for any AI.

Study distilled from the PandaiTech channel (t.me/pandaitech):
- Prompt engineering -> context engineering -> loop engineering: give the AI
  the context and rules first, then let it iterate; don't expect a one-shot
  magic prompt.
- "Humanise" after the fact does not work: feed brand references (voice rules
  with reasons, banned/used words, 3 before & after examples, per-output
  templates) BEFORE the AI writes.
- Small models need more hand-holding (explicit constraints and format) than
  big ones; reasoning models overthink unless you ask for realistic ideas.
- Not everything should be automated: a loop/agent is worth building only
  when the task repeats and manual checking would cost more.

Every prompt below is a COMPLETE, self-contained instruction — paste it into
any AI (ChatGPT, Claude, Gemini, Grok, Copilot, an agent or a coding tool)
and it works without follow-ups: role, context, task, constraints, output
format, verification and a next step are all in the one text. No fragments.
Output is a draft for humans to verify before use; nothing is published.
"""
import re

_MAX_TOPIC = 300

LANGS = {"en": "English", "bm": "Bahasa Melayu (Malay)"}
DEFAULT_LANG = "en"

_ROLE = ("You are a senior operator in this field. Be direct and practical, "
         "never pad the answer, and never invent numbers, facts, sources or "
         "quotes — when something is uncertain, mark it as an assumption. "
         "If any required information is missing, ask one short clarifying "
         "question before starting.")


def _topic(topic):
    t = re.sub(r"\s+", " ", (topic or "")).strip()
    return t[:_MAX_TOPIC] or "your product or topic"


def _lang_block(lang):
    return "Write the ENTIRE answer in " + LANGS[lang] + "."


# ---------------------------------------------------------------- templates ---
# Each entry: key -> (display label, builder(topic, lang) -> complete prompt)

def _social_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + "\n\n"
            "TASK: Create a 7-day social content plan for '" + t + "' — one post "
            "per day — for an audience that already knows this problem exists "
            "but is not yet sold on any solution.\n\n"
            "CONTEXT: The brand sells to a Malaysian market; the goal of week "
            "one is trust and clicks, not hard selling.\n\n"
            "CONSTRAINTS:\n"
            "- Day order must be: D1 hook (name the #1 frustration), D2 proof "
            "(one concrete, checkable result), D3 education (one myth vs the "
            "truth), D4 behind-the-scenes, D5 objection/FAQ (the #1 doubt), "
            "D6 quick-win tip, D7 soft CTA.\n"
            "- Every caption: max 120 words, one hook line first, one "
            "call-to-action last, at most 3 hashtags, no emoji spam, no "
            "generic phrases like 'game-changer', 'unlock', 'elevate'.\n"
            "- Any claim that needs a number must be written as a verifiable "
            "placeholder like [RESULT: fill with your real number].\n\n"
            "OUTPUT FORMAT:\n"
            "1) A table: Day | Angle | Caption (ready to paste) | CTA.\n"
            "2) A 3-line posting checklist (what to verify before each post).\n\n"
            "VERIFY BEFORE YOU STOP: re-read each caption as the audience, "
            "delete any sentence that could belong to any other brand, and "
            "confirm no invented numbers remain.\n\n"
            "NEXT STEP: tell me which 2 posts are weakest and rewrite them in "
            "one go.\n\n"
            + _lang_block(lang))


def _brand_voice_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + "\n\n"
            "TASK: Write a brand-voice reference document I can feed to any AI "
            "before it writes content for '" + t + "', so its output sounds "
            "like us and not like any other company.\n\n"
            "CONTEXT: AI output sounds generic because the AI has never seen "
            "our brand — the fix is to give it references BEFORE writing, not "
            "to ask it to 'humanise' afterwards. Examples beat adjectives.\n\n"
            "CONSTRAINTS: The document must contain exactly these sections:\n"
            "1) WHO — who we are, what we sell, who it is for (3 lines).\n"
            "2) ADDRESS — how we address the reader, which language mix (BM / "
            "English / campur) and when each is used.\n"
            "3) TONE — 3 tone words; for each: sounds like '[example sentence]', "
            "never sounds like '[example sentence]', and the reason.\n"
            "4) WORDS WE USE — 5-10 specific words/phrases we actually use.\n"
            "5) WORDS WE NEVER USE — 5 words we avoid and the replacement for "
            "each.\n"
            "6) BEFORE & AFTER — 3 pairs: a generic AI version of a sentence, "
            "then our version.\n"
            "7) OUTPUT TEMPLATES — one template for each output type we write "
            "most (e.g. caption: hook / body / CTA), with length limits.\n"
            "8) RULE — if information is missing, ask; never guess.\n\n"
            "OUTPUT FORMAT: Markdown with the 8 numbered sections. Where you "
            "do not yet know our real wording, use [PLACEHOLDER: ...] so I can "
            "fill it in — do not invent our voice on my behalf.\n\n"
            "VERIFY: after writing, check that section 6 actually sounds "
            "different from section 5's banned words, and that no section is "
            "empty filler.\n\n"
            "NEXT STEP: ask me for 5-10 of our best existing pieces of writing "
            "and tell me which placeholders to fill first.\n\n"
            + _lang_block(lang))


def _build_app_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + " You are also a pragmatic software builder: "
            "ship the smallest version that is genuinely useful.\n\n"
            "TASK: Build a complete, runnable internal web app for '" + t + "' "
            "that a non-technical team member can operate from a browser.\n\n"
            "CONTEXT: This is for internal use, one or two operators, hosted "
            "on a simple server. There is no existing system to integrate "
            "with yet. Data source for the app is [DATA: pick one — manual "
            "entry, an API, or a CSV upload].\n\n"
            "CONSTRAINTS:\n"
            "- Stack: Python (FastAPI) + a single HTML page with plain JS; "
            "no frontend framework, no build step, SQLite for storage.\n"
            "- Must include: a form, a list view, and an edit/delete action.\n"
            "- Must include: a README with exact run steps and a /health "
            "endpoint.\n"
            "- No login system yet (internal network); note where one would "
            "go if it ever becomes public.\n"
            "- Keep it under 300 lines of code total; simplicity beats "
            "features.\n\n"
            "OUTPUT FORMAT:\n"
            "1) A 5-line plan: screens, data model, endpoints.\n"
            "2) The complete code files, each under a 'FILE: <path>' header.\n"
            "3) Run instructions (3-5 commands).\n"
            "4) A 3-item acceptance checklist I can test in the browser.\n\n"
            "VERIFY: mentally run the code — every import exists, every "
            "endpoint is defined before it is called, the README commands "
            "match the file layout. Fix anything that would not run on the "
            "first try.\n\n"
            "NEXT STEP: list the 3 most likely ways to extend this and what "
            "the cost of each would be.\n\n"
            + _lang_block(lang))


def _research_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + " You are a research analyst.\n\n"
            "TASK: Produce a decision-ready research brief on '" + t + "' "
            "for a Malaysian business owner who will spend money on the "
            "outcome of this brief.\n\n"
            "CONTEXT: I will use this to decide within 2 weeks. I do not "
            "trust numbers that cannot be traced to a source.\n\n"
            "CONSTRAINTS:\n"
            "- Use only information you are confident is current; for "
            "anything you cannot verify, say so explicitly and mark it "
            "[UNVERIFIED].\n"
            "- Every figure must carry its source (name of the publication, "
            "site or document, and date if known). No source = no number.\n"
            "- Structure the brief so the decision comes first, not last.\n\n"
            "OUTPUT FORMAT:\n"
            "1) DECISION (3 lines): recommended option, the one condition "
            "that would change it, and the confidence level (high/medium/low).\n"
            "2) EVIDENCE: the top 5 findings, each with its source.\n"
            "3) RISKS: the 3 most likely ways this goes wrong, with a "
            "mitigation for each.\n"
            "4) COSTS: what it realistically costs (money or time), with "
            "ranges and sources.\n"
            "5) QUESTIONS: the 3 things I should check myself before "
            "committing.\n\n"
            "VERIFY: check that every number has a source, that the "
            "confidence level matches the evidence, and that the decision "
            "actually follows from sections 2-4.\n\n"
            "NEXT STEP: point out the weakest link in your own brief and "
            "explain what evidence would strengthen it.\n\n"
            + _lang_block(lang))


def _agent_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + " You are an autonomous AI agent with tools.\n\n"
            "TASK: Complete '" + t + "' end to end without further "
            "instructions, working in a loop until done or blocked.\n\n"
            "CONTEXT: I define what 'done' means up front so you cannot "
            "declare victory early. You may use available tools (search, "
            "files, code execution) as needed.\n\n"
            "LOOP RULES (context + verification, not one-shot):\n"
            "1) PLAN — write a numbered plan with 3-7 steps before doing "
            "anything; each step names its output.\n"
            "2) DO ONE STEP at a time.\n"
            "3) VERIFY — after each step, check the output against the step's "
            "definition of done; if it fails, fix and re-check (max 3 "
            "attempts per step).\n"
            "4) REPEAT until every step passes.\n"
            "5) STOP conditions — stop early and report if: a step fails 3 "
            "times, you need information only I can provide, or you are about "
            "to spend money. Never silently give up.\n\n"
            "DEFINITION OF DONE (all must be true):\n"
            "- [DONE-1]: state the specific, checkable outcome required.\n"
            "- [DONE-2]: every factual claim in the output has a source.\n"
            "- [DONE-3]: nothing was published, sent or billed without "
            "my explicit approval.\n\n"
            "CONSTRAINTS: realistic ideas only — no ideas that need more "
            "resources than I stated; keep total steps under 7; do not add "
            "scope I did not ask for.\n\n"
            "OUTPUT FORMAT: for each loop iteration report exactly: STEP "
            "n/total | action taken | verification result (pass/fail + why). "
            "Finish with a SUMMARY: what is done, what is not, what I must "
            "decide next.\n\n"
            "VERIFY: before the final summary, re-check every DONE item "
            "against your actual outputs, not your intentions.\n\n"
            "NEXT STEP: if stopped early, list the smallest action I can take "
            "to unblock you.\n\n"
            + _lang_block(lang))


def _video_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + " You are a short-video editor and scriptwriter "
            "who has shipped hundreds of TikToks and Shorts.\n\n"
            "TASK: Turn '" + t + "' into a 30-second vertical video: a "
            "narration-ready script, on-screen text beats, b-roll search "
            "terms and a publish caption.\n\n"
            "CONTEXT: Most viewers watch muted and decide in 3 seconds. The "
            "video must be filmable with a phone and stock footage.\n\n"
            "CONSTRAINTS:\n"
            "- Script: 4 paragraphs, no markdown, no 'welcome to this video', "
            "no stage directions, max 90 words total, same language as the "
            "subject.\n"
            "- Structure: [0-3s] hook, [3-10s] problem, [10-22s] three value "
            "points, [22-27s] one verifiable proof, [27-30s] one CTA.\n"
            "- B-roll terms: 1-3 words each, in script order, always include "
            "the main subject, max 8 terms.\n"
            "- Caption: max 200 characters, ends with the CTA, 3-5 hashtags.\n"
            "- Every on-screen claim must be one a viewer could verify; if a "
            "number is needed, write [FILL: real number].\n\n"
            "OUTPUT FORMAT:\n"
            "1) SCRIPT — raw narration text only.\n"
            "2) ON-SCREEN — beat-by-beat text card, one line per beat.\n"
            "3) B-ROLL — numbered search terms.\n"
            "4) CAPTION — ready to paste.\n"
            "5) 60s EXTENSION — the two beats that would be added and where.\n\n"
            "VERIFY: read the script aloud at normal speed; if it runs past "
            "30 seconds, cut it and re-report. Check no beat contains an "
            "unverifiable claim.\n\n"
            "NEXT STEP: suggest the single best alternative hook.\n\n"
            + _lang_block(lang))


def _generic_prompt(topic, lang):
    t = _topic(topic)
    return ("ROLE: " + _ROLE + "\n\n"
            "TASK: " + t + ".\n\n"
            "CONTEXT: Treat the task as one complete job with a clear finish "
            "line, not a conversation starter. If the task is ambiguous, pick "
            "the most common, sensible interpretation, state that assumption "
            "in one line, and proceed.\n\n"
            "CONSTRAINTS:\n"
            "- Realistic scope only — no ideas that need more resources than "
            "stated.\n"
            "- Every factual claim needs a source or the marker [UNVERIFIED].\n"
            "- If required information is missing, ask ONE question before "
            "starting; after that, work with what you have and label gaps.\n\n"
            "OUTPUT FORMAT: 1) The deliverable itself, complete and ready to "
            "use. 2) ASSUMPTIONS: the decisions you made on my behalf. "
            "3) CHECKS: what I should verify before using it. 4) NEXT: the "
            "smallest sensible follow-up.\n\n"
            "VERIFY: before finishing, re-check that the deliverable matches "
            "the task exactly as written and that no assumption is hidden "
            "inside it.\n\n"
            "NEXT STEP: point out the weakest part of your own output and how "
            "I would improve it with one more instruction.\n\n"
            + _lang_block(lang))


TEMPLATES = {
    "social": ("Social content (7-day plan + captions)", _social_prompt),
    "brand": ("Brand voice / writing style (anti-generic AI)", _brand_voice_prompt),
    "app": ("Build an internal app end to end", _build_app_prompt),
    "research": ("Research brief with cited evidence", _research_prompt),
    "agent": ("Autonomous agent: plan → do → verify loop", _agent_prompt),
    "video": ("Short-video package (script + b-roll + caption)", _video_prompt),
    "generic": ("Any task — complete prompt from your description", _generic_prompt),
}


def build_prompt(template_key, topic, lang=DEFAULT_LANG):
    """Return (prompt_text, label). Raises ValueError on an unknown key."""
    key = (template_key or "").strip().lower()
    if key not in TEMPLATES:
        raise ValueError("Unknown prompt template: " + (template_key or "?") +
                         " — available: " + ", ".join(sorted(TEMPLATES)))
    label, builder = TEMPLATES[key]
    lang = lang if lang in LANGS else DEFAULT_LANG
    return builder(_topic(topic), lang), label


def build_response(template_key, topic, lang=DEFAULT_LANG):
    """Format a built prompt as a Telegram-ready message (complete prompt first)."""
    prompt, label = build_prompt(template_key, topic, lang)
    lines = ["🧠 PROMPT LAB — " + label,
             "Topic: " + _topic(topic) + ("  (sample topic — reply with your own to regenerate)"
             if not (topic or "").strip() else ""),
             "",
             "👇 COMPLETE PROMPT — copy everything below this line 👇",
             "",
             prompt,
             "",
             "───",
             "Works in any AI: ChatGPT · Claude · Gemini · Grok · Codex · an "
             "agent loop. It carries role, context, constraints, output "
             "format, verification and a next step — no follow-ups needed.",
             "🔒 Draft — verify the output it produces before you publish or "
             "spend. Try another: /prompt (menu)."]
    return "\n".join(lines)[:3900]
