"""Regression tests for MART Telegram menu and callback routing (offline)."""
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
from telegram_ui import COMMANDS, keyboard

class TelegramMenuTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)

    def test_command_registry_unique_and_valid(self):
        names = [item["command"] for item in COMMANDS]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue({"start", "research", "campaign", "status", "help"}.issubset(names))
        self.assertTrue(all(name.islower() and name.isalnum() for name in names))

    def test_inline_keyboard_callbacks(self):
        buttons = [button for row in keyboard()["inline_keyboard"] for button in row]
        self.assertEqual(len(buttons), len({b["callback_data"] for b in buttons}))
        self.assertTrue({"status", "help"}.issubset({b["callback_data"] for b in buttons}))

    def test_start_and_menu_display_keyboard(self):
        for index, command in enumerate(("/start", "/menu"), 900001):
            with self.subTest(command=command), patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": "test-secret"}), patch.object(app.campaigns, "accept_update", return_value=True), patch.object(app, "send_message", new_callable=AsyncMock) as send:
                response = self.client.post("/telegram/webhook", headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"}, json={"update_id": index, "message": {"chat": {"id": 123}, "text": command}})
                self.assertEqual(response.status_code, 200)
                self.assertIn("MART Agentic", send.await_args.args[1])
                self.assertTrue(send.await_args.kwargs["menu"])

    def test_reject_missing_secret(self):
        with patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": "test-secret"}):
            response = self.client.post("/telegram/webhook", json={"update_id": 900004, "message": {"chat": {"id": 123}, "text": "/start"}})
            self.assertEqual(response.status_code, 403)

    def test_callback_status_and_help(self):
        for data, expected in (("status", "Service online"), ("help", "MART Research Bot")):
            with self.subTest(data=data), patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"}), patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post, patch.object(app, "send_message", new_callable=AsyncMock) as send:
                post.return_value.raise_for_status = lambda: None
                import asyncio
                asyncio.run(app.answer_callback({"id": "callback", "data": data, "message": {"chat": {"id": 123}}}))
                self.assertIn(expected, send.await_args.args[1])

if __name__ == "__main__":
    unittest.main()
