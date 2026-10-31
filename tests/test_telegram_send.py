import asyncio
import os
import unittest
from unittest.mock import patch
import httpx
from app import send_message

class FakeClient:
    def __init__(self, response):
        self.response = response
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def post(self, *args, **kwargs):
        return self.response

class TelegramSendTests(unittest.TestCase):
    def test_api_ok_false_raises(self):
        response = httpx.Response(200, json={"ok": False, "description": "rejected"}, request=httpx.Request("POST", "https://example.org"))
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}):
            with patch("app.httpx.AsyncClient", return_value=FakeClient(response)):
                with self.assertRaisesRegex(RuntimeError, "unsuccessful"):
                    asyncio.run(send_message(123, "hello"))

    def test_api_ok_true(self):
        response = httpx.Response(200, json={"ok": True, "result": {"message_id": 1}}, request=httpx.Request("POST", "https://example.org"))
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}):
            with patch("app.httpx.AsyncClient", return_value=FakeClient(response)):
                asyncio.run(send_message(123, "hello"))

if __name__ == "__main__":
    unittest.main()
