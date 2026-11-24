"""Offline tests for the Prompt Lab: complete, self-contained prompts for any AI."""
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import app
import campaigns
import menu_guide
import promptlab
from telegram_ui import ACTIONS

PARTS = ("ROLE:", "TASK:", "CONTEXT:", "CONSTRAINTS:", "OUTPUT FORMAT:",
         "VERIFY", "NEXT STEP:")


class PromptTemplateTests(unittest.TestCase):
    def test_all_templates_produce_complete_prompts(self):
        for key in promptlab.TEMPLATES:
            with self.subTest(key=key):
                prompt, label = promptlab.build_prompt(key, "mt5 for beginners")
                self.assertTrue(label)
                for part in PARTS:
                    self.assertIn(part, prompt, f"{key} prompt lacks {part!r}")
                self.assertIn("Write the ENTIRE answer in", prompt, key)
                self.assertIn("mt5 for beginners", prompt, key)
                self.assertLessEqual(len(prompt), 2400, key)

    def test_language_switch_bm(self):
        prompt, _ = promptlab.build_prompt("social", "gold signals", "bm")
        self.assertIn("Bahasa Melayu (Malay)", prompt)

    def test_unknown_language_falls_back_to_en(self):
        prompt, _ = promptlab.build_prompt("social", "gold signals", "xx")
        self.assertIn("Write the ENTIRE answer in English", prompt)

    def test_unknown_template_raises(self):
        with self.assertRaises(ValueError):
            promptlab.build_prompt("nope", "x")

    def test_topic_is_cleaned_and_capped(self):
        prompt, _ = promptlab.build_prompt("research", "  a   b " * 200)
        self.assertIn("a b a b", prompt)
        self.assertLessEqual(len(prompt), 2400)

    def test_empty_topic_uses_placeholder(self):
        prompt, _ = promptlab.build_prompt("agent", "")
        self.assertIn("your product or topic", prompt)

    def test_brand_template_has_the_voice_sections(self):
        prompt, _ = promptlab.build_prompt("brand", "our channel")
        for section in ("WHO", "TONE", "WORDS WE USE", "WORDS WE NEVER USE",
                        "BEFORE & AFTER", "OUTPUT TEMPLATES"):
            self.assertIn(section, prompt)

    def test_agent_template_is_a_loop_not_one_shot(self):
        prompt, _ = promptlab.build_prompt("agent", "report")
        for section in ("PLAN", "VERIFY", "REPEAT", "STOP conditions",
                        "DEFINITION OF DONE"):
            self.assertIn(section, prompt)

    def test_prompts_carry_honesty_rule(self):
        for key in promptlab.TEMPLATES:
            prompt, _ = promptlab.build_prompt(key, "x")
            self.assertIn("never invent", prompt, key)

    def test_response_is_complete_and_telegram_sized(self):
        for key in promptlab.TEMPLATES:
            with self.subTest(key=key):
                out = promptlab.build_response(key, "gold trading signals", "en")
                self.assertIn("COMPLETE PROMPT", out)
                self.assertIn("Works in any AI", out)
                self.assertTrue(out.startswith("🧠 PROMPT LAB"))
                self.assertLessEqual(len(out), 3900, key)

    def test_response_marks_sample_topic(self):
        out = promptlab.build_response("social", "", "en")
        self.assertIn("sample topic", out)


class PromptWebhookTests(unittest.TestCase):
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
            json={"update_id": 400000 + self._uid,
                  "message": {"chat": {"id": chat, "type": "private"},
                              "from": {"id": chat}, "text": text}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "offline"})

    def test_prompt_is_a_menu_action_with_guide(self):
        self.assertIn("prompt", ACTIONS)
        self.assertEqual(menu_guide.all_guide_kinds(), sorted(ACTIONS))
        g = menu_guide.guide("prompt")
        self.assertTrue(g.startswith("Selected:"))
        self.assertIn("deep dive", g)
        for needle in ("COMPLETE", "ROLE", "VERIFY", "agent", "bm"):
            self.assertIn(needle, g)

    def test_prompt_no_arg_returns_deep_dive(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/prompt").status_code, 200)
            text = send.await_args.args[1]
        self.assertTrue(text.startswith("Selected: 🧠 Prompt Lab"))
        self.assertIn("deep dive", text)
        self.assertIn("/prompt", text)

    def test_prompt_template_builds_complete_prompt(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(
                self.post("/prompt agent weekly competitor price report").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("COMPLETE PROMPT", text)
        for part in PARTS:
            self.assertIn(part, text)
        self.assertIn("weekly competitor price report", text)

    def test_prompt_generic_mode_wraps_arbitrary_task(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(
                self.post("/prompt compare 3 forex vps providers").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("COMPLETE PROMPT", text)
        self.assertIn("compare 3 forex vps providers", text)

    def test_prompt_bm_lang_token_is_consumed(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/prompt social gold signals bm").status_code, 200)
            text = send.await_args.args[1]
        self.assertIn("Bahasa Melayu (Malay)", text)

    def test_prompt_bare_lang_word_stays_topic(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/prompt bm").status_code, 200)
            text = send.await_args.args[1]
        # single token is the topic in generic mode, language stays the default
        self.assertIn("Write the ENTIRE answer in English", text)
        self.assertIn("bm", text)

    def test_callback_button_returns_deep_dive(self):
        with patch.object(app, "send_message", new_callable=AsyncMock) as send:
            self.assertEqual(self.post("/prompt").status_code, 200)
        import asyncio
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            post.return_value.raise_for_status = lambda: None
            result = asyncio.run(app.answer_callback(
                {"id": "t", "data": "action:prompt", "from": {"id": 50},
                 "message": {"chat": {"id": 50, "type": "private"}}}, send=False))
        self.assertTrue(result.startswith("Selected:"))
        self.assertIn("deep dive", result)


if __name__ == "__main__":
    unittest.main()
