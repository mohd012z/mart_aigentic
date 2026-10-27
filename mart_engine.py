"""Research engine with source diversity, scoring and safe Telegram formatting."""
import os
import re
from urllib.parse import urlparse
import httpx

def score(signals):
    """Transparent heuristic, not a prediction of financial returns."""
    weights = {"demand": 0.35, "competition": 0.20, "monetization": 0.25, "evidence": 0.20}
    return round(sum(max(0, min(5, float(signals.get(k, 0)))) * w for k, w in weights.items()) * 20, 1)

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

async def research(query, client=None):
    """Use Brave Search when configured; otherwise report missing provider explicitly."""
    token = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not token:
        return "Research provider not configured. Set BRAVE_SEARCH_API_KEY to enable live evidence-backed research."
    if not query or len(query) > 300:
        return "Provide a research topic of 1–300 characters."
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
            return "No verifiable sources found. Try a more specific query."
        lines = ["Research: " + query, "", "Evidence sources:"]
        for i, r in enumerate(results, 1):
            title = re.sub(r"<[^>]+>", "", r["title"]).strip()[:95]
            lines.append(f"{i}. {title}\n{r['url']}\n{re.sub(r'<[^>]+>', '', r['description'])[:170]}")
        lines.append("\nRecommendation: Compare demand, competition and monetization using the cited sources. These search results alone do not establish profitability.")
        return "\n\n".join(lines)[:3900]
    except (httpx.HTTPError, ValueError) as exc:
        return f"Research unavailable ({type(exc).__name__}). Retry later."
    finally:
        if owned:
            await client.aclose()
