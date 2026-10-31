import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class TelegramRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "retry-secret", "MART_CAMPAIGN_DB": self.temp.name + "/test.sqlite"})
        self.env.start()
        import campaigns
        self.previous_db = campaigns.DB
        campaigns.DB = self.temp.name + "/test.sqlite"
        from app import app
        self.client = TestClient(app)

    def tearDown(self):
        import campaigns
        campaigns.DB = self.previous_db
        self.env.stop()
        self.temp.cleanup()

    def test_failed_delivery_can_retry_same_update(self):
        update = {"update_id": 89123, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 123}, "text": "/start"}}
        headers = {"X-Telegram-Bot-Api-Secret-Token": "retry-secret"}
        with patch("app.send_message", new_callable=AsyncMock) as send:
            send.side_effect = [RuntimeError("Telegram unavailable"), None]
            with self.assertRaises(RuntimeError):
                self.client.post("/telegram/webhook", json=update, headers=headers)
            response = self.client.post("/telegram/webhook", json=update, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(send.await_count, 2)
            self.client.post("/telegram/webhook", json=update, headers=headers)
            self.assertEqual(send.await_count, 2)

if __name__ == "__main__":
    unittest.main()
