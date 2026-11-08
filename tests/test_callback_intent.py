"""Offline callback intent, crash, authorization and restart regression tests."""
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import update_journal as journal

class CallbackIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "callback.sqlite")
        self.env = patch.dict(os.environ, {"MART_CAMPAIGN_DB": self.path})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def session(self):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT chat,user,action FROM sessions").fetchall()

    def test_atomic_session_and_intent_survive_restart(self):
        _, generation = journal.claim(1)
        journal.prepare_callback(1, generation, 50, "Send topic", user=50, action="campaign")
        self.assertEqual(self.session(), [(50, 50, "campaign")])
        self.assertEqual(journal.claim(1)[0], "reply_pending")
        self.assertIn((1, "reply_pending"), journal.recoverable())

    def test_stale_generation_has_no_session_side_effect(self):
        _, old = journal.claim(2, now=100, lease_seconds=1)
        _, current = journal.claim(2)
        with self.assertRaises(RuntimeError):
            journal.prepare_callback(2, old, 50, "old", user=50, action="campaign")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone()[0], 0)
        journal.prepare_callback(2, current, 50, "new", user=50, action="campaign")
        self.assertEqual(self.session(), [(50, 50, "campaign")])

    def test_unauthorized_callback_rolls_back_intent(self):
        _, generation = journal.claim(3)
        with self.assertRaises(ValueError):
            journal.prepare_callback(3, generation, 50, "invalid", user=51, action="campaign")
        self.assertEqual(journal.claim(3)[0], "processing")

    def test_duplicate_callback_does_not_reselect(self):
        _, generation = journal.claim(4)
        journal.prepare_callback(4, generation, 50, "reply", user=50, action="campaign")
        with self.assertRaises(RuntimeError):
            journal.prepare_callback(4, generation, 50, "reply", user=50, action="campaign")
        self.assertEqual(self.session(), [(50, 50, "campaign")])

    def test_concurrent_callback_only_one_wins(self):
        _, generation = journal.claim(5)
        def attempt(_):
            try:
                journal.prepare_callback(5, generation, 50, "reply", user=50, action="campaign")
                return True
            except RuntimeError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(attempt, range(12)))
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(self.session(), [(50, 50, "campaign")])

    def test_ack_failure_leaves_durable_pending_state(self):
        _, generation = journal.claim(6)
        journal.prepare_callback(6, generation, 50, "reply", user=50, action="campaign")
        # Simulate process death before external callback acknowledgment.
        self.assertEqual(journal.claim(6)[0], "reply_pending")
        self.assertIn((6, "reply_pending"), journal.recoverable())
        self.assertEqual(self.session(), [(50, 50, "campaign")])

if __name__ == "__main__":
    unittest.main()
