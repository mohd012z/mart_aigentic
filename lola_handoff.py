"""Authenticated MART -> LOLA advisory handoff contract (offline, no network).

Transport owner must enforce TLS and persist replay IDs before forwarding.
No bot token, model invocation, publishing or Telegram API calls here.
"""
import hashlib
import hmac
import json
import time

MAX_AGE_SECONDS = 300
MAX_BYTES = 8192


def sign_handoff(payload: dict, secret: str, *, now: int | None = None) -> tuple[bytes, str]:
    if not secret or len(secret) < 32:
        raise ValueError("Handoff secret must be at least 32 characters")
    data = dict(payload)
    data["issued_at"] = int(time.time() if now is None else now)
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ValueError("Handoff too large")
    return body, hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_handoff(body: bytes, signature: str, secret: str, *, now: int | None = None) -> dict:
    if not secret or len(secret) < 32:
        raise ValueError("Invalid handoff secret")
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        raise ValueError("Invalid handoff size")
    if not isinstance(signature, str) or len(signature) != 64:
        raise PermissionError("Invalid signature")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise PermissionError("Invalid signature")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload")
    issued = payload.get("issued_at")
    now = int(time.time() if now is None else now)
    if type(issued) is not int or issued > now + 30 or now - issued > MAX_AGE_SECONDS:
        raise PermissionError("Expired handoff")
    if payload.get("bot_username", "").lstrip("@").casefold() != "mart_aigenticbot":
        raise PermissionError("Unexpected bot")
    for key in ("user_id", "chat_id", "update_id"):
        if type(payload.get(key)) is not int:
            raise ValueError("Invalid " + key)
    if payload["user_id"] <= 0 or payload["chat_id"] == 0 or payload["update_id"] < 0:
        raise ValueError("Invalid identity")
    if not isinstance(payload.get("text"), str) or not 0 < len(payload["text"].strip()) <= 4096:
        raise ValueError("Invalid message")
    if payload.get("requires_execution", False) is not False:
        raise PermissionError("Execution not authorized")
    return payload
