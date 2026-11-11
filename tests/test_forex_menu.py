"""Offline tests for the forex no-deposit bonus list and forex affiliate link store."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
import affiliate_catalog
import forex_bonuses

class BonusStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "bonus.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_is_idempotent(self):
        self.assertGreater(forex_bonuses.seed(self.db), 0)
        self.assertEqual(forex_bonuses.seed(self.db), 0)
        self.assertEqual(len(forex_bonuses.list_bonuses(self.db)), len(forex_bonuses.SEED))

    def test_expiry_filtering(self):
        forex_bonuses.seed(self.db)
        self.assertGreater(len(forex_bonuses.list_bonuses(self.db, as_of="2026-12-01")), 0)
        # After all validity dates, only ongoing (empty validity) entries remain.
        rows = forex_bonuses.list_bonuses(self.db, as_of="2030-01-01")
        for r in rows:
            self.assertEqual(r["validity"], "")

    def test_add_bonus_roundtrip(self):
        forex_bonuses.add_bonus(self.db, "TestBroker", "$50", "new clients", "2026-12-31", "https://example.com/b")
        rows = forex_bonuses.list_bonuses(self.db)
        self.assertIn("TestBroker", [r["broker"] for r in rows])


class ForexLinkStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "offers.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_file_loads_and_idempotent(self):
        seed = os.path.join(os.path.dirname(os.path.abspath(app.__file__)), "seeds", "forex_affiliate.json")
        self.assertGreater(affiliate_catalog.seed_from_file(self.db, seed), 0)
        self.assertEqual(affiliate_catalog.seed_from_file(self.db, seed), 0)
        rows = affiliate_catalog.list_offers(self.db, category="forex")
        self.assertEqual(len(rows), 3)
        self.assertIn("justmarkets", [r["merchant"] for r in rows])
        self.assertIn("fbs", [r["merchant"] for r in rows])
        self.assertIn("roboforex", [r["merchant"] for r in rows])
        for r in rows:
            self.assertEqual(r["category"], "forex")

    def test_general_category_excludes_forex_seeds(self):
        seed = os.path.join(os.path.dirname(os.path.abspath(app.__file__)), "seeds", "forex_affiliate.json")
        affiliate_catalog.seed_from_file(self.db, seed)
        affiliate_catalog.add_offer(self.db, "Generic", "Generic", "https://example.org/g",
                                    "https://example.org/g", "2026-11-11")
        self.assertEqual(len(affiliate_catalog.list_offers(self.db, category="general")), 1)
        self.assertEqual(len(affiliate_catalog.list_offers(self.db)), 4)


class ForexWebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MART_CAMPAIGN_DB": os.path.join(self.tmp.name, "mart.sqlite3"),
            "MART_AFFILIATE_DB": os.path.join(self.tmp.name, "offers.sqlite3"),
            "MART_BONUS_DB": os.path.join(self.tmp.name, "bonus.sqlite3"),
            "TELEGRAM_WEBHOOK_SECRET": "offline-test-secret",
            "TELEGRAM_BOT_TOKEN": "offline-unused-token",
        })
        self.env.start()
        self.client = TestClient(app.app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.tmp.cleanup()

    def post(self, payload, secret="offline-test-secret", private=True):
        return self.client.post("/telegram/webhook", json=payload,
                                headers={"X-Telegram-Bot-Api-Secret-Token": secret})

    def private_msg(self, uid, chat, text):
        return {"update_id": uid, "message": {"chat": {"id": chat, "type": "private"},
                                              "from": {"id": chat}, "text": text}}

    def test_forexbonus_lists_seeded_bonuses(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post(self.private_msg(910, 123, "/forexbonus")).status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("No-Deposit Bonus", text)
        self.assertIn("XM", text)
        self.assertIn("https://", text)
        self.assertIn("No-deposit bonuses change", text)

    def test_forexa_list_includes_stored_links(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post(self.private_msg(920, 123, "/forexa list")).status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("justmarkets", text)
        self.assertIn("https://one.justmarkets.link/a/pqgpr0vvea", text)
        self.assertIn("fbs", text)
        self.assertIn("https://fbs.partners?ibl=189965&ibp=1139886", text)
        self.assertIn("roboforex", text)
        self.assertIn("https://my.roboinvesting.pro/en/?a=eree", text)

    def test_forexa_add_share_remove_roundtrip(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.post(self.private_msg(930, 123, "/forexa add xm-my https://example.com/?p=1"))
            added = send.await_args.args[1]
            self.assertIn("Stored 'xm-my'", added)
            self.post(self.private_msg(931, 123, "/forexa share xm-my"))
            shared = send.await_args.args[1]
            self.assertIn("Copy & share:", shared)
            self.assertIn("https://example.com/?p=1", shared)
            self.assertIn("Affiliate disclosure:", shared)
            self.post(self.private_msg(932, 123, "/forexa remove xm-my"))
            removed = send.await_args.args[1]
            self.assertIn("Removed 'xm-my'", removed)
            self.post(self.private_msg(933, 123, "/forexa list"))
            listing = send.await_args.args[1]
            self.assertNotIn("https://example.com/?p=1", listing)

    def test_forexa_requires_http2(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.post(self.private_msg(940, 123, "/forexa add bad http://example.com/x"))
            self.assertIn("must start with https://", send.await_args.args[1])

    def test_forexa_blocked_in_group_chat(self):
        payload = {"update_id": 950, "message": {"chat": {"id": 5, "type": "group"},
                                                 "from": {"id": 999}, "text": "/forexa list"}}
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post(payload).status_code, 200)
            self.assertIn("private chat", send.await_args.args[1].lower())


if __name__ == "__main__":
    unittest.main()
