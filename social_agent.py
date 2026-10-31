"""Platform-aware marketing drafts. Offline and approval-only; no platform API calls."""
from dataclasses import dataclass
from typing import Dict

PLATFORMS = {
    "facebook": {"format": "Page post", "limit": 1800, "media": "optional"},
    "instagram": {"format": "Caption for an image or reel", "limit": 1500, "media": "required for publishing"},
    "threads": {"format": "Short conversational post", "limit": 450, "media": "optional"},
    "tiktok": {"format": "Short video storyboard and caption", "limit": 1200, "media": "video required for publishing"},
    "tiktok_shop": {"format": "Product video concept", "limit": 1200, "media": "depends on seller permissions"},
    "shopee": {"format": "Product listing improvement", "limit": 1800, "media": "depends on listing"},
}

def draft(platform: str, product: str, facts: str = "", affiliate: bool = False) -> Dict[str, object]:
    platform = platform.strip().lower()
    if platform not in PLATFORMS:
        raise ValueError("Unsupported platform")
    product = product.strip()
    facts = facts.strip()
    if not product or len(product) > 180 or len(facts) > 1500:
        raise ValueError("Invalid product or facts length")
    config = PLATFORMS[platform]
    lines = [f"{product}", "", "Product overview:"]
    lines.append(facts if facts else "Add verified product specifications and benefits before publishing.")
    lines.extend(["", "Check the current price, availability and any promotional terms before posting.",
                  "CTA: View the product details and decide whether it meets your needs."])
    if affiliate:
        lines.insert(0, "Affiliate disclosure: I may earn a commission from qualifying purchases.\n")
    body = "\n".join(lines)[:config["limit"]]
    return {"platform": platform, "format": config["format"], "draft": body,
            "requires_review": True, "published": False,
            "api_connected": False, "media_requirement": config["media"]}

def platform_status():
    return {name: {"api_connected": False, "publishing_enabled": False}
            for name in PLATFORMS}
