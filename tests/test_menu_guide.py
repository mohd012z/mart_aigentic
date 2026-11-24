"""Offline tests: deep-dive guides are served for every menu action and command."""
import asyncio
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
import campaigns
import menu_guide
from telegram_ui import ACTIONS


class GuideContentTests(unittest.TestCase):
    def test_every_action_has_a_guide(self):
        self.assertEqual(menu_guide.all_guide_kinds(), sorted(ACTIONS))

    def test_guides_have_depth_and_topic_specifics(self):
        expected = {
            "campaign": ("queued", "running", "review", "campaignstatus"),
            "research": ("HTTPS", "Deduplicated", "1–300", "no verifiable sources"),
            "recommend": ("35%", "20%", "25%", "0–100", "triage aid"),
            "marketing": ("OBJECTIVE", "AUDIENCE", "CHANNELS", "FUNNEL",
                          "BUDGET", "KPI", "30-DAY CALENDAR"),
            "ads": ("headlines", "Meta", "Google", "TikTok", "A/B"),
            "social": ("7-day", "D1 hook", "Malay", "one-line question"),
            "video": ("30s", "60s", "0–3s hook", "9:16", "SRT"),
            "contentlab": ("SCRIPT", "STOCK TERMS", "SOURCES", "offline"),
            "prompt": ("COMPLETE", "ROLE", "VERIFY", "agent", "bm"),
            "affiliate": ("VERIFIED CATALOG", "disclosure", "/forexa add"),
            "forexbonus": ("validity", "lead, not an offer", "source URL"),
            "forexa": ("/forexa add", "/forexa share", "/forexa remove", "https"),
        }
        for kind, needles in expected.items():
            g = menu_guide.guide(kind)
            self.assertTrue(g, f"missing guide for {kind}")
            for needle in needles:
                self.assertIn(needle, g, f"{kind} guide lacks {needle!r}")

    def test_guides_are_within_telegram_limit_and_labeled_selected(self):
        for kind in ACTIONS:
            g = menu_guide.guide(kind)
            self.assertLessEqual(len(g), 4000, kind)
            self.assertTrue(g.startswith("Selected:"), kind)

    def test_unknown_kind_returns_none(self):
        self.assertIsNone(menu_guide.guide("not-a-menu-item"))

    def test_campaign_guide_mentions_flow_not_publishing(self):
        g = menu_guide.guide("campaign")
        self.assertIn("nothing is published", g.lower())


class GuideWebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mart.sqlite")
        self.old_db = campaigns.DB
        campaigns.DB = self.path
        self.env = patch.dict(os.environ, {
            "MART_CAMPAIGN_DB": self.path,
            "MART_AFFILIATE_DB": os.path.join(self.tmp.name, "offers.sqlite3"),
            "MART_BONUS_DB": os.path.join(self.tmp.name, "bonus.sqlite3"),
            "TELEGRAM_WEBHOOK_SECRET": "offline",
            "TELEGRAM_BOT_TOKEN": "offline",
        })
        self.env.start()
        self.client = TestClient(app.app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        campaigns.DB = self.old_db
        self.tmp.cleanup()

    def post(self, text, chat=77):
        self._uid = getattr(self, "_uid", 0) + 1
        return self.client.post(
            "/telegram/webhook",
            json={"update_id": 300000 + self._uid,
                  "message": {"chat": {"id": chat, "type": "private"},
                              "from": {"id": chat}, "text": text}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "offline"})

    def test_noarg_action_commands_return_deep_dive(self):
        for kind in ACTIONS:
            with self.subTest(kind=kind):
                with patch.object(app, "send_message", new_callable=AsyncMock) as send:
                    self.assertEqual(self.post("/" + kind).status_code, 200)
                    text = send.await_args.args[1]
                    self.assertTrue(text.startswith("Selected:"), kind)
                    self.assertIn("deep dive", text, kind)

    def test_command_args_still_generate_content(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/marketing forex signals").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("MARKETING PLAN", text)
        self.assertNotIn("deep dive", text)

    def test_contentlab_offline_returns_labelled_package(self):
        os.environ.pop("MART_LLM_API_KEY", None)
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/contentlab solar panels for homes").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("CONTENT LAB — solar panels for homes", text)
        self.assertIn("SCRIPT", text)
        self.assertIn("HASHTAGS", text)
        self.assertIn("STOCK TERMS", text)
        self.assertIn("script=offline_template", text)
        self.assertIn("Nothing published", text)
        self.assertLessEqual(len(text), 4096)

    def test_contentlab_platform_token_is_consumed(self):
        os.environ.pop("MART_LLM_API_KEY", None)
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/contentlab solar panels instagram_reels").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("Instagram Reels", text)
        self.assertNotIn("tiktok", text.lower())

    def test_contentlab_bare_platform_word_stays_topic(self):
        os.environ.pop("MART_LLM_API_KEY", None)
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/contentlab tiktok").status_code, 200)
            text = send.await_args.args[1]
        # single token is the topic, platform stays the default
        self.assertIn("CONTENT LAB — tiktok", text)
        self.assertIn("TikTok", text)

    def test_contentlab_no_arg_returns_deep_dive(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/contentlab").status_code, 200)
            text = send.await_args.args[1]
        self.assertTrue(text.startswith("Selected: 🎥 Content Lab"))
        self.assertIn("deep dive", text)
        self.assertIn("/contentlab <topic>", text)

    def test_noarg_campaign_selects_session_and_returns_guide(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/campaign").status_code, 200)
            text = send.await_args.args[1]
        self.assertTrue(text.startswith("Selected: 🚀 Campaign"))
        self.assertIn("queued", text)
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT chat,user,action FROM sessions").fetchall()
        self.assertEqual(rows, [(77, 77, "campaign")])

    def test_noarg_forexbonus_button_path_returns_guide_plus_current_list(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/forexbonus").status_code, 200)
            text = send.await_args.args[1]
        self.assertTrue(text.startswith("Selected: 💵 Forex No-Deposit Bonus"))
        self.assertIn("lead, not an offer", text)
        self.assertIn("XM", text)  # current seeded list still shown after the guide
        self.assertLessEqual(len(text), 4000)

    def test_noarg_forexa_button_path_returns_guide_plus_list(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/forexa").status_code, 200)
            text = send.await_args.args[1]
        self.assertTrue(text.startswith("Selected: 🔗 Forex Affiliate Links"))
        self.assertIn("/forexa add", text)
        self.assertIn("justmarkets", text)  # seeded catalog shown after the guide
        self.assertLessEqual(len(text), 4000)


class GuideCallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mart.sqlite")
        self.old_db = campaigns.DB
        campaigns.DB = self.path

    def tearDown(self):
        campaigns.DB = self.old_db
        self.tmp.cleanup()

    def invoke(self, data, chat=50, user=50, chat_type="private"):
        callback = {"id": "test", "data": data, "from": {"id": user},
                    "message": {"chat": {"id": chat, "type": chat_type}}}
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "offline-token",
                                     "MART_CAMPAIGN_DB": self.path}), \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            post.return_value.raise_for_status = lambda: None
            return asyncio.run(app.answer_callback(callback, send=False))

    def test_action_buttons_return_deep_dive(self):
        for kind in ACTIONS:
            with self.subTest(kind=kind):
                result = self.invoke("action:" + kind)
                self.assertTrue(result.startswith("Selected:"), kind)
                self.assertIn("deep dive", result, kind)

    def test_campaign_button_selects_session_and_returns_guide(self):
        result = self.invoke("action:campaign")
        self.assertTrue(result.startswith("Selected: 🚀 Campaign"))
        self.assertIn("queued", result)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT chat,user,action FROM sessions").fetchall(),
                             [(50, 50, "campaign")])

    def test_campaign_button_denied_in_group_returns_recovery_hints(self):
        with campaigns.conn():  # ensure the sessions table exists for the assertion
            pass
        result = self.invoke("action:campaign", chat=-100, user=20, chat_type="supergroup")
        self.assertIn("private chat only", result)
        self.assertIn("tap 🚀 Campaign", result)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sessions").fetchone()[0], 0)

    def test_unknown_action_falls_back_to_menu(self):
        result = self.invoke("action:ghost")
        self.assertIn("MART", result)


if __name__ == "__main__":
    unittest.main()
