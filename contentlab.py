"""MART content lab: topic -> video script, social metadata, stock terms, optional TTS.

Design distilled from the MoneyPrinter family:
- MoneyPrinterTurbo: constrained script system prompt + markdown cleaning;
  platform spec table (title/caption limits, hashtag counts); JSON social
  metadata with embedded-JSON recovery and heuristic fallback.
- MoneyPrinterV2: staged pipeline (topic -> script -> TTS -> subtitles ->
  video -> upload) with every stage optional and gated on configuration.
- MoneyPrinterTurbo-Extended: stock-term generation matched to script order
  as the search layer for stock footage.

Everything works OFFLINE: when no LLM is configured (MART_LLM_API_KEY) or the
provider call fails, each stage returns a clearly labelled fallback draft.
Publishing stays disabled; the output is a reviewable content package.
"""
import json
import os
import re

import httpx

# Platform limits for social copy. Keep conservative: shorter is safer when
# a human publishes by hand. Values mirror the MPT platform spec shape.
SOCIAL_PLATFORMS = {
    "tiktok": {"title_max": 100, "caption_max": 1600, "hashtag_count": 5, "label": "TikTok"},
    "youtube_shorts": {"title_max": 100, "caption_max": 2000, "hashtag_count": 3, "label": "YouTube Shorts"},
    "instagram_reels": {"title_max": 125, "caption_max": 1600, "hashtag_count": 8, "label": "Instagram Reels"},
    "facebook_reels": {"title_max": 125, "caption_max": 1600, "hashtag_count": 5, "label": "Facebook Reels"},
}
DEFAULT_PLATFORM = "tiktok"
DEFAULT_SOCIAL_HASHTAGS = ["#shorts", "#viral", "#trending", "#fyp", "#video", "#reels", "#creator", "#content"]
MAX_TOPIC_LENGTH = 300

SCRIPT_SYSTEM_PROMPT = """Generate a script for a short video, depending on the subject of the video.

## Constrains:
1. the script is to be returned as a string with the specified number of paragraphs.
2. do not under any circumstance reference this prompt in your response.
3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. you must not include any type of markdown or formatting in the script, never use a title.
5. only return the raw content of the script.
6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line.
7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.
8. respond in the same language as the video subject.
"""

_MAX_RETRIES = 2


def llm_configured():
    """An OpenAI-compatible chat endpoint is usable when a key is set."""
    return bool(os.getenv("MART_LLM_API_KEY"))


def _chat(prompt, timeout=20):
    """One OpenAI-compatible chat call. Returns text, or raises on failure."""
    base = os.getenv("MART_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("MART_LLM_MODEL", "gpt-4o-mini")
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            base + "/chat/completions",
            headers={"Authorization": "Bearer " + os.environ["MART_LLM_API_KEY"]},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def _strip_code_fence(text):
    """Remove a surrounding markdown code fence (LLMs wrap JSON in ``` often)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _extract_embedded_json(text, opening):
    """Recover the first balanced JSON object/array from noisy LLM output."""
    start = (text or "").find(opening)
    if start < 0:
        return None
    closing = "}" if opening == "{" else "]"
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except ValueError:
                    return None
    return None


def _clamp_text(text, limit):
    text = (text or "").strip()
    return text[:limit]


def _resolve_platform(platform):
    return platform if platform in SOCIAL_PLATFORMS else DEFAULT_PLATFORM


def clean_script(text):
    """Turn raw LLM output into narration text (MPT generate_script format_response).

    Removes markdown emphasis/headings, link destinations and bracketed stage
    directions, and strips 'voiceover:' style prefixes. Music-note spellings
    such as C# and F# are preserved.
    """
    t = (text or "").strip()
    t = re.sub(r"(?mi)^(?:voiceover|narrator|speaker|vo)[:\s]+", "", t)
    # [label](url) -> label, so destinations don't get narrated
    t = re.sub(r"\[([^\]\n]+)\]\((?:[^()\n]|\\([^()\\n]*\\))*\)", r"\1", t)
    t = re.sub(r"\[.*?\]", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    t = t.replace("*", "")
    t = re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(.*?)[ \t]*$",
               lambda m: re.sub(r"[ \t]+#+[ \t]*$", "", m.group(1)), t)
    paragraphs = [p.strip() for p in t.split("\n\n")]
    return "\n\n".join(p for p in paragraphs if p)


def _fallback_script(topic, tone):
    """Offline script: a plain template draft, clearly labelled, never silent."""
    t = topic[:120]
    if tone:
        t2 = t + " — in a " + tone.lower() + " tone."
    else:
        t2 = t
    return ("[offline draft — no LLM configured]\n"
            "Hook: Here is what most people get wrong about " + t2 + "\n\n"
            "Point 1: Explain the single biggest problem with " + t + " in one plain sentence.\n"
            "Point 2: Show the practical fix or comparison in 20 seconds.\n"
            "Point 3: Give one concrete number or example a viewer can check.\n\n"
            "CTA: Follow for more, and tell us in the comments which part you would try first.\n\n"
            "Verify every factual claim before publishing.")


def generate_script(topic, tone="", client=None):
    """Return (script_text, source_label). Falls back to template when offline."""
    topic = (topic or "").strip()
    if not 1 <= len(topic) <= MAX_TOPIC_LENGTH:
        return "", "invalid"
    if not llm_configured():
        return _fallback_script(topic, tone), "offline_template"
    prompt = SCRIPT_SYSTEM_PROMPT + "\n\n# Initialization:\n- video subject: " + topic
    if tone:
        prompt += "\n- tone: " + tone[:80]
    prompt += "\n- number of paragraphs: 4"
    last = None
    for _ in range(_MAX_RETRIES):
        try:
            script = clean_script(_strip_code_fence(_chat(prompt)))
            if script:
                return script[:2400], "llm"
            last = ValueError("empty script")
        except Exception as exc:
            last = exc
    print("contentlab script LLM failed:", type(last).__name__, last)
    return _fallback_script(topic, tone), "llm_fallback"


def _normalize_hashtags(raw, count):
    """Clean LLM hashtags into "#tag" form; dedupe; default when empty (MPT shape)."""
    if isinstance(raw, str):
        candidates = re.split(r"[\s,，、;；#]+", raw)
    elif isinstance(raw, (list, tuple)):
        candidates = [str(entry) for entry in raw]
    else:
        candidates = []
    seen, tags = set(), []
    for item in candidates:
        tag = re.sub(r"[^0-9a-zA-Z_\u00C0-\uFFFF]+", "", item)
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append("#" + tag)
        if len(tags) >= count:
            break
    return tags or list(DEFAULT_SOCIAL_HASHTAGS[:count])


def _fallback_sentence(text):
    """First sentence for a fallback title; never split on '1.' numbered tips."""
    m = re.search(r"(?<=[.!?])\s+(?!\d+[.)])", text or "")
    if m:
        return (text or "")[:m.start()]
    return (text or "")[:100]


def social_metadata(topic, script, platform=DEFAULT_PLATFORM):
    """Return ({"title","caption","hashtags"}, source_label)."""
    platform = _resolve_platform(platform)
    spec = SOCIAL_PLATFORMS[platform]
    if llm_configured():
        prompt = ("Write publishing metadata for a short video for " + spec["label"] + ".\n"
                  "Respond ONLY with a single valid minified JSON object, no markdown, keys exactly:\n"
                  '{"title","caption","hashtags"}\n'
                  "title: catchy hook, max " + str(spec["title_max"]) + " chars.\n"
                  "caption: engaging description ending with a call to action, max " + str(spec["caption_max"]) + " chars, no hashtags inside.\n"
                  "hashtags: JSON array of exactly " + str(spec["hashtag_count"]) + ' strings, each starting with "#", no spaces.\n\n'
                  "### Video Subject\n" + topic + "\n\n### Video Script\n" + (script or "")[:4000])
        for _ in range(_MAX_RETRIES):
            try:
                raw = _strip_code_fence(_chat(prompt))
                try:
                    data = json.loads(raw)
                except ValueError:
                    data = _extract_embedded_json(raw, "{")
                if not isinstance(data, dict):
                    raise ValueError("not a JSON object")
                title = _clamp_text(data.get("title"), spec["title_max"])
                caption = _clamp_text(data.get("caption"), spec["caption_max"])
                hashtags = _normalize_hashtags(data.get("hashtags"), spec["hashtag_count"])
                if title or caption:
                    return {"title": title, "caption": caption, "hashtags": hashtags}, "llm"
            except Exception as exc:
                print("contentlab metadata parse failed:", type(exc).__name__, exc)
    meta = {
        "title": _clamp_text(topic or _fallback_sentence(script or ""), spec["title_max"]),
        "caption": _clamp_text((script or topic)[:spec["caption_max"]], spec["caption_max"]),
        "hashtags": DEFAULT_SOCIAL_HASHTAGS[:spec["hashtag_count"]],
    }
    return meta, "offline_heuristic"


def stock_terms(topic, script="", count=5):
    """Return (terms_list, source_label): search terms for stock footage sites.

    MPT-style rules: 1-3 words, always include the main subject, cover the
    script chronologically when a script is given.
    """
    topic = (topic or "").strip()
    script = (script or "").strip()
    count = max(3, min(int(count), 8))
    if llm_configured() and script:
        prompt = ("Generate " + str(count) + " chronological stock-video search terms that follow "
                  "the order of topics in this video script.\n"
                  "Rules: each term 1-3 words; always add the main subject of the video; "
                  "earlier terms describe earlier visual moments; reply with ONLY a JSON array of strings.\n\n"
                  "### Subject\n" + topic + "\n\n### Script\n" + script[:4000])
        for _ in range(_MAX_RETRIES):
            try:
                data = _extract_embedded_json(_strip_code_fence(_chat(prompt)), "[")
                if isinstance(data, list):
                    terms = [t.strip() for t in data if isinstance(t, str) and t.strip()]
                    if terms:
                        return [t[:40] for t in terms[:count]], "llm"
            except Exception as exc:
                print("contentlab terms parse failed:", type(exc).__name__, exc)
    subject = topic[:40].replace('"', "")
    terms = ([subject, subject + " problem", subject + " process",
              subject + " people", subject + " closeup"][:count]) if subject else []
    return terms, "offline_keyword"


def generate_voice(text, output_path, voice="alloy"):
    """OpenAI-compatible /audio/speech TTS. Returns (ok, status_note).

    Gated on configuration: when MART_TTS_API_KEY / MART_TTS_MODEL are absent
    the stage is skipped with a clear note instead of failing the package.
    """
    key = os.getenv("MART_TTS_API_KEY")
    model = os.getenv("MART_TTS_MODEL")
    if not key or not model:
        return False, "TTS not configured (set MART_TTS_API_KEY + MART_TTS_MODEL); script is narration-ready."
    base = os.getenv("MART_TTS_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                base + "/audio/speech",
                headers={"Authorization": "Bearer " + key},
                json={"model": model, "input": text[:4000], "voice": voice[:40] or "alloy"},
            )
            response.raise_for_status()
            with open(output_path, "wb") as fh:
                fh.write(response.content)
        return True, "voiceover saved: " + output_path
    except Exception as exc:
        return False, "TTS failed (" + type(exc).__name__ + "); script is narration-ready."


def generate_content_package(topic, platform=DEFAULT_PLATFORM, tone=""):
    """Full offline-capable content package. Returns (markdown_text, stage_labels)."""
    topic = (topic or "").strip()
    if not 1 <= len(topic) <= MAX_TOPIC_LENGTH:
        raise ValueError("Invalid topic")
    platform = _resolve_platform(platform)
    script, script_source = generate_script(topic, tone)
    if not script:
        return ("CONTENT LAB — " + topic + "\n\nScript generation failed; retry later.",
                {"script": "failed"})
    meta, meta_source = social_metadata(topic, script, platform)
    terms, terms_source = stock_terms(topic, script)
    lines = [
        "CONTENT LAB — " + topic,
        "Platform: " + SOCIAL_PLATFORMS[platform]["label"],
        "",
        "SCRIPT",
        script[:2400],
        "",
        "TITLE", meta["title"] or "(empty)",
        "",
        "CAPTION",
        meta["caption"] or "(empty)",
        "",
        "HASHTAGS",
        " ".join(meta["hashtags"]) or "(none)",
        "",
        "STOCK TERMS (chronological)",
    ]
    lines.extend(" - " + t for t in terms)
    lines.extend([
        "",
        "SOURCES: script=" + script_source + " metadata=" + meta_source + " terms=" + terms_source,
        "TTS: see /contentlab output when a TTS provider is configured.",
        "",
        "Review factual claims, copyright and platform rules. Nothing published.",
    ])
    labels = {"script": script_source, "metadata": meta_source, "terms": terms_source}
    return "\n".join(lines)[:3800], labels
