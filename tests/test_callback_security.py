"""Offline callback authorization and idempotent campaign tests."""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import app
import campaigns

class CallbackSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = campaigns.DB
        campaigns.DB = os.path.join(self.tmp.name, "campaign.sqlite")

    def tearDown(self):
        campaigns.DB = self.old
        self.tmp.cleanup()

    def invoke(self, chat_id, user_id, chat_type):
        callback = {"id": "test", "data": "action:campaign",
                    "from": {"id": user_id},
                    "message": {"chat": {"id": chat_id, "type": chat_type}}}
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "offline-token"}), patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            post.return_value.raise_for_status = lambda: None
            return asyncio.run(app.answer_callback(callback, send=False))

    def test_group_campaign_denied(self):
        self.assertIn("private chat", self.invoke(-100, 20, "supergroup"))
        self.assertIsNone(campaigns.consume(-100, 20))

    def test_private_user_must_match_chat(self):
        self.assertIn("private chat", self.invoke(10, 20, "private"))
        self.assertIsNone(campaigns.consume(10, 20))

    def test_private_user_allowed(self):
        self.assertIn("Send a product", self.invoke(20, 20, "private"))
        self.assertEqual(campaigns.consume(20, 20), "campaign")

    def test_campaign_creation_is_idempotent(self):
        first = campaigns.create(20, "earbuds", 778)
        second = campaigns.create(20, "earbuds", 778)
        self.assertEqual(first, second)
        with campaigns.conn() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM campaigns WHERE id=?", (first,)).fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
