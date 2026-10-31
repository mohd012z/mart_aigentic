"""Webhook failure and retry regression tests (no external Telegram calls)."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class TelegramWebhookReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "test-secret"})
        self.env.start()
        import campaigns
        self.old_db = campaigns.DB
        campaigns.DB = self.tmp.name + "/webhook.sqlite3"
        from app import app
        self.client = TestClient(app)

    def tearDown(self):
        import campaigns
        campaigns.DB = self.old_db
        self.env.stop()
        self.tmp.cleanup()

    def test_failed_delivery_can_be_retried(self):
        payload = {"update_id": 801234, "message": {
            "chat": {"id": 123, "type": "private"},
            "from": {"id": 123}, "text": "/start"}}
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
        with patch("app.send_message", new_callable=AsyncMock) as send:
            send.side_effect = RuntimeError("simulated delivery error")
            with self.assertRaises(RuntimeError):
                self.client.post("/telegram/webhook", json=payload, headers=headers)
            send.side_effect = None
            response = self.client.post("/telegram/webhook", json=payload, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(send.await_count, 2)

    def test_wrong_secret_is_forbidden(self):
        response = self.client.post("/telegram/webhook",
            json={"update_id": 801235},
            headers={"X-Telegram-Bot-Api-Secret-Token": "incorrect"})
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
