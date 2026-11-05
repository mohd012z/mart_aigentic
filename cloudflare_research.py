"""Authenticated MART-to-Cloudflare research queue adapter.

This module never registers Telegram webhooks or handles bot tokens.
"""
import hashlib
import os
from urllib.parse import urlsplit
import httpx


def configuration():
    endpoint = os.getenv("MART_RESEARCH_WORKER_URL", "").rstrip("/")
    key = os.getenv("MART_INTERNAL_KEY", "")
    if not endpoint or not key:
        return None
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
        return None
    return endpoint, key


def job_id(update_id, chat_id, command):
    value = f"{update_id}:{chat_id}:{command}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:40]


async def enqueue(update_id, chat_id, query, command, client=None):
    cfg = configuration()
    if cfg is None:
        return None
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 300:
        raise ValueError("Research topic must be 2–300 characters.")
    endpoint, key = cfg
    payload = {"id": job_id(update_id, chat_id, command), "chat_id": str(chat_id), "query": query.strip()}
    owned = client is None
    if owned:
        client = httpx.AsyncClient(timeout=12)
    try:
        response = await client.post(endpoint + "/enqueue",
            json=payload, headers={"Authorization": "Bearer " + key})
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError("Research queue rejected request")
        return payload["id"]
    finally:
        if owned:
            await client.aclose()
