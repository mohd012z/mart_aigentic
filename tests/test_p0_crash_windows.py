"""P0 crash-window, migration concurrency, and callback ordering regression tests."""
import asyncio
import os
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
import campaigns
import update_journal as journal

class P0Regression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mart.sqlite")
        self.old_db = campaigns.DB
        campaigns.DB = self.path
        self.env = patch.dict(os.environ, {"MART_CAMPAIGN_DB": self.path,
                                            "TELEGRAM_WEBHOOK_SECRET": "offline",
                                            "TELEGRAM_BOT_TOKEN": "offline"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        campaigns.DB = self.old_db
        self.tmp.cleanup()

    def test_expired_prepared_delivery_is_fenced(self):
        _, owner = journal.claim(100)
        journal.prepare(100, owner, 1, "reply")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE update_journal SET lease_until=0 WHERE id=100")
        self.assertFalse(journal.begin_delivery(100, owner))
        self.assertIn((100, "reply_pending"), journal.recoverable())

    def test_atomic_session_consumption_restart_and_duplicate(self):
        campaigns.select(1, 2, "campaign")
        cid = campaigns.consume_and_create(1, 2, "topic", 101)
        self.assertEqual(cid, campaigns.consume_and_create(1, 2, "topic", 101))
        self.assertIsNone(campaigns.consume(1, 2))
        self.assertIsNone(campaigns.consume_and_create(1, 2, "different", 102))
        with campaigns.conn() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM campaigns").fetchone()[0], 1)

    def test_atomic_session_rollback_on_invalid_topic(self):
        campaigns.select(1, 2, "campaign")
        with self.assertRaises(ValueError):
            campaigns.consume_and_create(1, 2, "", 103)
        self.assertEqual(campaigns.consume(1, 2), "campaign")

    def test_concurrent_legacy_migration(self):
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE update_journal(
                id INTEGER PRIMARY KEY,state TEXT NOT NULL,lease_until REAL NOT NULL DEFAULT 0,
                chat INTEGER,reply TEXT,updated REAL NOT NULL)""")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: journal.claim(200), range(16)))
        self.assertEqual(sum(state == "process" for state, _ in results), 1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(sum(r[1] == "generation" for r in db.execute("PRAGMA table_info(update_journal)")), 1)

    def test_callback_ack_after_reply_persisted(self):
        seen = []
        original_prepare = journal.prepare
        async def acknowledge(_callback):
            with sqlite3.connect(self.path) as db:
                seen.append(db.execute("SELECT state FROM update_journal WHERE id=201").fetchone()[0])
        with patch.object(app, "acknowledge_callback", side_effect=acknowledge), \
             patch.object(app, "send_message", new_callable=AsyncMock), \
             patch.object(app, "answer_callback", new_callable=AsyncMock, return_value="ready"):
            result = TestClient(app.app).post("/telegram/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "offline"},
                json={"update_id": 201, "callback_query": {"id": "x", "data": "help",
                    "message": {"chat": {"id": 1, "type": "private"}}}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(seen, ["reply_pending"])

    def test_callback_ack_failure_does_not_send(self):
        with patch.object(app, "acknowledge_callback", new_callable=AsyncMock, side_effect=RuntimeError("offline failure")), \
             patch.object(app, "send_message", new_callable=AsyncMock) as send, \
             patch.object(app, "answer_callback", new_callable=AsyncMock, return_value="ready"):
            with self.assertRaises(RuntimeError):
                TestClient(app.app, raise_server_exceptions=True).post("/telegram/webhook",
                    headers={"X-Telegram-Bot-Api-Secret-Token": "offline"},
                    json={"update_id": 202, "callback_query": {"id": "x", "data": "help",
                        "message": {"chat": {"id": 1, "type": "private"}}}})
            send.assert_not_awaited()
        self.assertIn((202, "reply_pending"), journal.recoverable())

if __name__ == "__main__":
    unittest.main()
