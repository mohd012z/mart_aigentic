"""Offline durable update-journal failure and recovery regression tests."""
import os
import tempfile
import unittest
from unittest.mock import patch
import update_journal as journal

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"MART_CAMPAIGN_DB": os.path.join(self.tmp.name, "journal.sqlite")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_duplicate_and_expired_lease(self):
        self.assertEqual(journal.claim(1, now=100, lease_seconds=10), "process")
        self.assertEqual(journal.claim(1, now=105), "processing")
        self.assertEqual(journal.claim(1, now=110), "process")

    def test_reply_pending_recovery_is_not_automatically_resent(self):
        self.assertEqual(journal.claim(2), "process")
        journal.prepare(2, 123, "hello")
        self.assertEqual(journal.claim(2), "reply_pending")
        self.assertIn((2, "reply_pending"), journal.recoverable())

    def test_uncertain_delivery_requires_reconciliation(self):
        journal.claim(3)
        journal.prepare(3, 123, "hello")
        self.assertTrue(journal.begin_delivery(3))
        self.assertFalse(journal.begin_delivery(3))
        self.assertEqual(journal.claim(3), "delivery_uncertain")
        self.assertIn((3, "delivery_uncertain"), journal.recoverable())
        journal.delivered(3)
        self.assertEqual(journal.claim(3), "delivered")

    def test_reject_invalid_update_id(self):
        for uid in ("1", None, True):
            with self.subTest(uid=uid), self.assertRaises(ValueError):
                journal.claim(uid)

    def test_concurrent_claim_single_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: journal.claim(4), range(16)))
        self.assertEqual(results.count("process"), 1)

if __name__ == "__main__":
    unittest.main()
