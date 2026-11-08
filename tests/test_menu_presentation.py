"""Offline MART menu registry and callback side-effect safety tests."""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import app
import campaigns
from telegram_ui import ACTIONS, COMMANDS, keyboard, menu_text

class MenuPresentationTests(unittest.TestCase):
    def test_registered_commands_include_menu(self):
        commands = [item["command"] for item in COMMANDS]
        self.assertEqual(len(commands), len(set(commands)))
        self.assertIn("menu", commands)
        self.assertLessEqual(len(commands), 100)
        self.assertTrue(all(len(c) <= 32 for c in commands))

    def test_all_action_buttons_have_routes(self):
        data = [button["callback_data"] for row in keyboard()["inline_keyboard"] for button in row]
        self.assertEqual(len(data), len(set(data)))
        self.assertTrue({"status", "help", "menu"}.issubset(data))
        self.assertEqual({item.removeprefix("action:") for item in data if item.startswith("action:")}, set(ACTIONS))
        self.assertTrue(all(len(item.encode("utf-8")) <= 64 for item in data))

    def test_menu_text_safe_research_only(self):
        self.assertIn("MART", menu_text())
        self.assertIn("no automatic publishing", menu_text())

    def test_deferred_callback_has_no_session_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = campaigns.DB
            campaigns.DB = os.path.join(tmp, "mart.sqlite")
            try:
                callback = {"id": "offline", "data": "action:campaign",
                            "from": {"id": 50},
                            "message": {"chat": {"id": 50, "type": "private"}}}
                result = asyncio.run(app.answer_callback(callback, send=False,
                                                           acknowledge=False, select_session=False))
                self.assertIn("Send a product", result)
                self.assertIsNone(campaigns.consume(50, 50))
            finally:
                campaigns.DB = old

if __name__ == "__main__":
    unittest.main()
