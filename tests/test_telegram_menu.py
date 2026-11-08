import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import app
import campaigns
from telegram_ui import ACTIONS, COMMANDS, keyboard, menu_text


class FakeTelegramResponse:
    def raise_for_status(self):
        return None


class FakeTelegramClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json):
        if not url.endswith("/answerCallbackQuery"):
            raise AssertionError("Unexpected Telegram method")
        return FakeTelegramResponse()


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class TelegramMenuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        campaigns.DB = os.path.join(self.temp_dir.name, "mart.sqlite3")
        self.secret = patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "test-secret"})
        self.secret.start()
        self.addCleanup(self.secret.stop)
        self.send = AsyncMock()
        self.sender = patch("app.send_message", self.send)
        self.sender.start()
        self.addCleanup(self.sender.stop)

    def tearDown(self):
        self.temp_dir.cleanup()

    async def call_webhook(self, update_id, text):
        return await app.telegram_webhook(
            FakeRequest({
                "update_id": update_id,
                "message": {
                    "chat": {"id": 100, "type": "private"},
                    "from": {"id": 200},
                    "text": text,
                },
            }),
            "test-secret",
        )

    async def test_start_and_menu_show_inline_dashboard(self):
        for update_id, command in ((1, "/start"), (2, "/menu")):
            await self.call_webhook(update_id, command)
            args = self.send.await_args.args
            self.assertIn("Choose a tool below", args[1])
            self.assertTrue(self.send.await_args.kwargs["menu"])

    async def test_help_and_status_shortcuts_have_distinct_responses(self):
        await self.call_webhook(3, "/help")
        help_text = self.send.await_args.args[1]
        self.assertIn("/menu", help_text)
        self.assertNotIn("Choose a tool below", help_text)

        await self.call_webhook(4, "/status")
        status_text = self.send.await_args.args[1]
        self.assertIn("Service online", status_text)

    async def test_keyboard_callbacks_and_commands_are_registered(self):
        markup = keyboard()["inline_keyboard"]
        callback_values = {
            button["callback_data"]
            for row in markup
            for button in row
        }
        self.assertEqual(
            callback_values,
            {f"action:{key}" for key in ACTIONS} | {"status", "help"},
        )
        self.assertTrue(
            all(len(value.encode("utf-8")) <= 64 for value in callback_values)
        )

        commands = {item["command"] for item in COMMANDS}
        self.assertEqual(len(commands), len(COMMANDS))
        self.assertTrue({"menu", "start", "help", "status", *ACTIONS}.issubset(commands))
        self.assertIn("slash shortcut", menu_text())

    async def test_unknown_callback_returns_menu_without_network(self):
        with patch("app.httpx.AsyncClient", return_value=FakeTelegramClient()):
            await app.answer_callback({
                "id": "callback-1",
                "data": "stale",
                "message": {"chat": {"id": 100}},
            })
        self.send.assert_awaited_once()
        self.assertIn("Choose a tool below", self.send.await_args.args[1])


if __name__ == "__main__":
    unittest.main()
