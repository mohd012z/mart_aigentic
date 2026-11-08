"""Offline SQLite fencing, migration, restart and concurrency tests."""
import os
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import update_journal as journal

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "journal.sqlite")
        self.env = patch.dict(os.environ, {"MART_CAMPAIGN_DB": self.path})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_duplicate_and_expired_lease(self):
        self.assertEqual(journal.claim(1, now=100, lease_seconds=10), ("process", 1))
        self.assertEqual(journal.claim(1, now=105)[0], "processing")
        self.assertEqual(journal.claim(1, now=110), ("process", 2))

    def test_pending_restart(self):
        _, token = journal.claim(2)
        journal.prepare(2, token, 123, "hello")
        self.assertEqual(journal.claim(2)[0], "reply_pending")
        self.assertIn((2, "reply_pending"), journal.recoverable())

    def test_uncertain_delivery(self):
        _, token = journal.claim(3)
        journal.prepare(3, token, 123, "hello")
        self.assertTrue(journal.begin_delivery(3, token))
        self.assertFalse(journal.begin_delivery(3, token))
        self.assertEqual(journal.claim(3)[0], "delivery_uncertain")
        self.assertTrue(journal.delivered(3, token))
        self.assertFalse(journal.delivered(3, token))
        self.assertEqual(journal.claim(3)[0], "delivered")

    def test_invalid_ids(self):
        for uid in ("1", None, True, -1):
            with self.subTest(uid=uid), self.assertRaises(ValueError):
                journal.claim(uid)

    def test_concurrent_single_owner(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: journal.claim(4), range(16)))
        self.assertEqual(sum(state == "process" for state, _ in results), 1)

    def test_stale_worker_rejected_after_reclaim(self):
        _, old = journal.claim(5, now=time.time() - 1000, lease_seconds=1)
        _, current = journal.claim(5)
        self.assertGreater(current, old)
        with self.assertRaises(RuntimeError):
            journal.prepare(5, old, 123, "stale")
        journal.prepare(5, current, 123, "current")
        self.assertFalse(journal.begin_delivery(5, old))
        self.assertTrue(journal.begin_delivery(5, current))
        self.assertFalse(journal.delivered(5, old))
        self.assertTrue(journal.delivered(5, current))

    def test_expired_owner_cannot_prepare(self):
        _, owner = journal.claim(6, now=time.time()-1000, lease_seconds=1)
        with self.assertRaises(RuntimeError):
            journal.prepare(6, owner, 123, "late")

    def test_legacy_schema_migrates(self):
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE update_journal(id INTEGER PRIMARY KEY,state TEXT NOT NULL,
                lease_until REAL NOT NULL DEFAULT 0,chat INTEGER,reply TEXT,updated REAL NOT NULL)""")
            db.execute("INSERT INTO update_journal VALUES(7,'processing',0,NULL,NULL,0)")
        self.assertEqual(journal.claim(7), ("process", 1))
        with sqlite3.connect(self.path) as db:
            self.assertIn("generation", [row[1] for row in db.execute("PRAGMA table_info(update_journal)")])

if __name__ == "__main__":
    unittest.main()
