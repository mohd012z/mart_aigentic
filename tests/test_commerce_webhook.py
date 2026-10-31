"""Regression tests for the feature-flagged commerce Telegram webhook."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class CommerceWebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MART_CAMPAIGN_DB": self.tmp.name + "/updates.sqlite",
            "TELEGRAM_WEBHOOK_SECRET": "test-webhook-secret",
            "MART_COMMERCE_ENABLED": "1",
            "MART_COMMERCE_ALLOWED_USER_IDS": "123",
        })
        self.env.start()
        import campaigns
        self.old_db = campaigns.DB
        campaigns.DB = self.tmp.name + "/updates.sqlite"
        from app import app
        self.client = TestClient(app)
        self.send = patch("app.send_message", new_callable=AsyncMock)
        self.sender = self.send.start()

    def tearDown(self):
        self.send.stop()
        import campaigns
        campaigns.DB = self.old_db
        self.env.stop()
        self.tmp.cleanup()

    def post(self, update_id, uid=123, chat_type="private", text="/commerce threads USB cable", secret="test-webhook-secret"):
        body = {"update_id": update_id, "message": {
            "chat": {"id": 123, "type": chat_type},
            "from": {"id": uid}, "text": text}}
        return self.client.post("/telegram/webhook", json=body,
            headers={"X-Telegram-Bot-Api-Secret-Token": secret})

    def test_owner_draft(self):
        self.assertEqual(self.post(101).status_code, 200)
        message = self.sender.await_args.args[1]
        self.assertIn("NOT PUBLISHED", message)
        self.assertIn("USB cable", message)

    def test_unauthorized_user(self):
        self.assertEqual(self.post(102, uid=999).status_code, 200)
        self.assertIn("denied", self.sender.await_args.args[1])

    def test_group_denied(self):
        self.assertEqual(self.post(103, chat_type="group").status_code, 200)
        self.assertIn("denied", self.sender.await_args.args[1])

    def test_bad_secret(self):
        self.assertEqual(self.post(104, secret="wrong").status_code, 403)
        self.sender.assert_not_awaited()

    def test_duplicate_update(self):
        self.post(105)
        self.post(105)
        self.assertEqual(self.sender.await_count, 1)

    def test_disabled(self):
        os.environ["MART_COMMERCE_ENABLED"] = "0"
        self.post(106)
        self.assertIn("disabled", self.sender.await_args.args[1])

if __name__ == "__main__":
    unittest.main()
