"""Local webhook contract checks; no Telegram network calls."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class TelegramStartContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "contract-secret"})
        self.env.start()
        import campaigns
        self.old_db = campaigns.DB
        campaigns.DB = self.temp.name + "/updates.sqlite3"
        from app import app
        self.client = TestClient(app)

    def tearDown(self):
        import campaigns
        campaigns.DB = self.old_db
        self.env.stop()
        self.temp.cleanup()

    def test_start_returns_menu_and_commands(self):
        update = {"update_id": 901001, "message": {
            "chat": {"id": 111, "type": "private"},
            "from": {"id": 111}, "text": "/start"}}
        with patch("app.send_message", new_callable=AsyncMock) as send:
            response = self.client.post("/telegram/webhook", json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": "contract-secret"})
            self.assertEqual(response.status_code, 200)
            send.assert_awaited_once()
            self.assertIn("MART", send.await_args.args[1])
            self.assertTrue(send.await_args.kwargs["menu"])

    def test_missing_secret_rejected(self):
        response = self.client.post("/telegram/webhook", json={"update_id": 901002})
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
