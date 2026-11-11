"""Research engine with source diversity, scoring and safe Telegram formatting.

/research  returns the evidence list (unchanged format).
/recommend returns a differentiated brief: compact evidence plus a transparent
heuristic signal score built from the cited sources (score(), previously unused).
/affiliate serves verified catalog offers first (affiliate_catalog), then evidence,
and always appends the disclosure line.
"""
import os
import re
from urllib.parse import urlparse
import httpx

def score(signals):
    """Transparent heuristic, not a prediction of financial returns."""
    weights = {"demand": 0.35, "competition": 0.20, "monetization": 0.25, "evidence": 0.20}
    return round(sum(max(0, min(5, float(signals.get(k, 0)))) * w for k, w in weights.items()) * 20, 1)

def clean(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()

def unique_results(items, limit=6):
    seen, domains, out = set(), set(), []
    for item in items:
        url = item.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        key = (parsed.hostname.lower(), parsed.path.rstrip("/").lower())
        if key in seen:
            continue
        seen.add(key)
        if parsed.hostname in domains and len(out) < 3:
            continue
        domains.add(parsed.hostname)
        out.append(item)
        if len(out) >= limit:
            break
    return out

async def fetch_results(query, client=None):
    """Return (results, None) on success or (None, message) when unavailable."""
    token = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not token:
        return None, "Research provider not configured. Set BRAVE_SEARCH_API_KEY to enable live evidence-backed research."
    if not query or len(query) > 300:
        return None, "Provide a research topic of 1–300 characters."
    owned = client is None
    if owned:
        client = httpx.AsyncClient(timeout=18)
    try:
        response = await client.get("https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 12},
            headers={"X-Subscription-Token": token, "Accept": "application/json"})
        response.raise_for_status()
        items = response.json().get("web", {}).get("results", [])
        results = unique_results([{"title": x.get("title", "Untitled"), "url": x.get("url", ""), "description": x.get("description", "")} for x in items])
        if not results:
            return None, "No verifiable sources found. Try a more specific query."
        return results, None
    except (httpx.HTTPError, ValueError) as exc:
        return None, f"Research unavailable ({type(exc).__name__}). Retry later."
    finally:
        if owned:
            await client.aclose()

async def research(query, client=None):
    """Use Brave Search when configured; otherwise report missing provider explicitly."""
    results, message = await fetch_results(query, client)
    if message:
        return message
    lines = ["Research: " + query, "", "Evidence sources:"]
    for i, r in enumerate(results, 1):
        title = clean(r["title"])[:95]
        lines.append(f"{i}. {title}\n{r['url']}\n{clean(r['description'])[:170]}")
    lines.append("\nRecommendation: Compare demand, competition and monetization using the cited sources. These search results alone do not establish profitability.")
    return "\n\n".join(lines)[:3900]

def signal_signals(results):
    """Derive the four 0–5 heuristic inputs from cited source text only.

    Transparent by construction: each count is reproducible from the returned
    evidence, and the result is never presented as a market forecast.
    """
    def hits(*terms):
        count = 0
        for r in results:
            text = (clean(r["title"]) + " " + clean(r["description"])).lower()
            if any(t in text for t in terms):
                count += 1
        return min(5, count)
    domains = {urlparse(r["url"]).hostname for r in results}
    return {
        "demand": hits("demand", "buy", "purchase", "trend", "growth", "popular", "search for"),
        "competition": 5 - hits("competitor", "market share", "alternative", "vs ", "versus", "top 10"),
        "monetization": hits("price", "commission", "profit", "revenue", "earn", "paying", "margin"),
        "evidence": min(5, len(domains)),
    }

async def recommend(query, client=None):
    """Evidence plus a transparent heuristic signal score (different from /research)."""
    results, message = await fetch_results(query, client)
    if message:
        return message
    signals = signal_signals(results)
    total = score(signals)
    lines = ["Recommendation brief: " + query, ""]
    lines.append("Key evidence (top 4):")
    for i, r in enumerate(results[:4], 1):
        lines.append(f"{i}. {clean(r['title'])[:90]} — {r['url']}")
    lines.append("")
    lines.append(
        "Initial signal score: %s/100\n"
        "demand %d · competition (headroom) %d · monetization %d · evidence %d\n"
        "Signals are keyword counts over the cited sources — a triage aid, not a market forecast."
        % (total, signals["demand"], signals["competition"], signals["monetization"], signals["evidence"])
    )
    lines.append(
        "Verify before committing budget: actual search demand, competitor pricing, "
        "real commission/price data from the cited sources, and unit economics."
    )
    return "\n".join(lines)[:3900]

async def affiliate_brief(query, catalog_db, client=None):
    """Verified offers (never invented) first, then evidence, disclosure always."""
    import affiliate_catalog
    catalog_lines = []
    try:
        offers = affiliate_catalog.list_offers(catalog_db, limit=10)
        needle = (query or "").lower()
        matches = [o for o in offers
                   if needle in o["title"].lower() or needle in o["merchant"].lower()]
        if not matches and len(offers) <= 3:
            matches = offers  # a small curated catalog is relevant to any topic
        for o in matches[:3]:
            commission = o.get("commission_text") or "commission not listed — verify"
            catalog_lines.append(
                f"• {o['merchant']} — {o['title']}\n{o['url']}\n"
                f"Commission: {commission} · Verified {o['verified_at']}\n"
                f"Source: {o['source_url']}"
            )
    except (ValueError, OSError):
        catalog_lines = []
    results, message = await fetch_results(query, client)
    if message:
        return message
    lines = ["Affiliate research: " + query, ""]
    if catalog_lines:
        lines.append("Verified offers (catalog, never invented):")
        lines.extend(catalog_lines)
        lines.append("")
    lines.append("Market evidence:")
    for i, r in enumerate(results[:4], 1):
        lines.append(f"{i}. {clean(r['title'])[:90]} — {r['url']}")
    lines.append("")
    lines.append(affiliate_catalog.ADD_DISCLOSURE)
    return "\n".join(lines)[:3900]
