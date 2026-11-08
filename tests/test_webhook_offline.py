"""Offline webhook behavior and failure-boundary regression tests."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
import update_journal


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MART_CAMPAIGN_DB": os.path.join(self.temp.name, "mart.sqlite3"),
            "TELEGRAM_WEBHOOK_SECRET": "offline-test-secret",
            "TELEGRAM_BOT_TOKEN": "offline-unused-token",
        })
        self.env.start()
        self.client = TestClient(app.app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def post(self, payload, secret="offline-test-secret"):
        return self.client.post("/telegram/webhook", json=payload,
                                headers={"X-Telegram-Bot-Api-Secret-Token": secret})

    def test_rejects_wrong_secret(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            response = self.post({"update_id": 1}, secret="wrong")
            self.assertEqual(response.status_code, 403)
            send.assert_not_awaited()

    def test_rejects_missing_update_id(self):
        response = self.post({"message": {"chat": {"id": 9}, "text": "/start"}})
        self.assertEqual(response.status_code, 400)

    def test_start_delivers_inline_menu(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            response = self.post({"update_id": 2, "message": {"chat": {"id": 9}, "text": "/start"}})
            self.assertEqual(response.status_code, 200)
            send.assert_awaited_once()
            args, kwargs = send.await_args
            self.assertEqual(args[0], 9)
            self.assertTrue(kwargs["menu"])
            self.assertEqual(update_journal.claim(2)[0], "delivered")

    def test_duplicate_does_not_send_twice(self):
        payload = {"update_id": 3, "message": {"chat": {"id": 9}, "text": "/menu"}}
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post(payload).status_code, 200)
            self.assertEqual(self.post(payload).status_code, 200)
            send.assert_awaited_once()

    def test_send_failure_is_not_marked_delivered(self):
        payload = {"update_id": 4, "message": {"chat": {"id": 9}, "text": "/start"}}
        with patch.object(app, "send_message", new_callable=AsyncMock, side_effect=RuntimeError("offline simulated failure")) as send:
            with self.assertRaises(RuntimeError):
                self.post(payload)
            self.assertEqual(update_journal.claim(4)[0], "delivery_uncertain")
            self.assertIn((4, "delivery_uncertain"), update_journal.recoverable())
            self.assertEqual(self.post(payload).status_code, 200)
            send.assert_awaited_once()

    def test_restart_recovers_pending_as_visible_not_resending(self):
        state, owner = update_journal.claim(5)
        self.assertEqual(state, "process")
        update_journal.prepare(5, owner, 9, "prepared offline")
        self.assertIn((5, "reply_pending"), update_journal.recoverable())
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            response = self.post({"update_id": 5, "message": {"chat": {"id": 9}, "text": "/start"}})
            self.assertEqual(response.status_code, 200)
            send.assert_not_awaited()
            self.assertEqual(update_journal.claim(5)[0], "reply_pending")


if __name__ == "__main__":
    unittest.main()
