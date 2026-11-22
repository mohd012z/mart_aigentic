import os
import unittest
import contentlab


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.old_key = os.environ.pop("MART_LLM_API_KEY", None)
        os.environ.pop("MART_TTS_API_KEY", None)

    def tearDown(self):
        if self.old_key is not None:
            os.environ["MART_LLM_API_KEY"] = self.old_key

    def test_offline_script_labelled(self):
        script, source = contentlab.generate_script("solar panels for homes")
        self.assertEqual(source, "offline_template")
        self.assertIn("solar panels for homes", script)
        self.assertTrue(script.startswith("[offline draft"))

    def test_invalid_topic(self):
        self.assertEqual(contentlab.generate_script("")[1], "invalid")
        self.assertEqual(contentlab.generate_script("x" * 301)[1], "invalid")

    def test_clean_script_removes_markdown(self):
        raw = ("# Title here\n\n**Bold** intro [link](https://x.test/a) and note.\n\n"
               "## Second\nvoiceover: keep going with C# music reference.")
        cleaned = contentlab.clean_script(raw)
        self.assertNotIn("#", cleaned.split("C#")[0])
        self.assertIn("C#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("https://x.test/a", cleaned)
        self.assertIn("link", cleaned)

    def test_fallback_metadata_respects_limits(self):
        meta, source = contentlab.social_metadata("a", "b" * 5000, "instagram_reels")
        self.assertEqual(source, "offline_heuristic")
        self.assertLessEqual(len(meta["title"]), contentlab.SOCIAL_PLATFORMS["instagram_reels"]["title_max"])
        self.assertEqual(len(meta["hashtags"]), contentlab.SOCIAL_PLATFORMS["instagram_reels"]["hashtag_count"])
        for tag in meta["hashtags"]:
            self.assertTrue(tag.startswith("#"))

    def test_fallback_terms_chronological_shape(self):
        terms, source = contentlab.stock_terms("drones", "intro\nmid\nend", 4)
        self.assertEqual(source, "offline_keyword")
        self.assertEqual(len(terms), 4)
        self.assertTrue(terms[0].startswith("drones"))

    def test_tts_skip_when_unconfigured(self):
        ok, note = contentlab.generate_voice("hello", "/tmp/never.mp3")
        self.assertFalse(ok)
        self.assertIn("not configured", note)

    def test_package_offline(self):
        text, labels = contentlab.generate_content_package("forex risk management")
        self.assertIn("CONTENT LAB", text)
        self.assertIn("SOURCES: script=offline_template", text)
        self.assertIn("Nothing published", text)
        self.assertEqual(labels["script"], "offline_template")

    def test_package_invalid_topic(self):
        with self.assertRaises(ValueError):
            contentlab.generate_content_package("")


class LlmMockedTests(unittest.TestCase):
    def setUp(self):
        self.old_key = os.environ.pop("MART_LLM_API_KEY", None)
        os.environ["MART_LLM_API_KEY"] = "test-key"

    def tearDown(self):
        contentlab._chat = self.old_chat
        if self.old_key is not None:
            os.environ["MART_LLM_API_KEY"] = self.old_key
        else:
            os.environ.pop("MART_LLM_API_KEY", None)

    def test_script_via_mocked_chat(self):
        self.old_chat = contentlab._chat

        def fake_chat(prompt, timeout=20):
            return "```markdown\n# Hook\nGreat hook line.\n\nPoint two here.\n```"

        contentlab._chat = fake_chat
        script, source = contentlab.generate_script("topic x")
        self.assertEqual(source, "llm")
        self.assertIn("Great hook line.", script)
        self.assertNotIn("```", script)
        self.assertNotIn("# Hook", script)

    def test_metadata_json_with_fence(self):
        self.old_chat = contentlab._chat

        def fake_chat(prompt, timeout=20):
            return '```json\n{"title": "Hook", "caption": "End with a CTA", "hashtags": ["a b", "c", 7, "#d"]}\n```'

        contentlab._chat = fake_chat
        meta, source = contentlab.social_metadata("topic", "script body", "tiktok")
        self.assertEqual(source, "llm")
        self.assertEqual(meta["title"], "Hook")
        self.assertEqual(meta["hashtags"], ["#ab", "#c", "#7", "#d"])

    def test_metadata_embedded_json_recovery(self):
        self.old_chat = contentlab._chat

        def fake_chat(prompt, timeout=20):
            return 'Sure! Here you go: {"title": "T2", "caption": "C2", "hashtags": ["#x"]} done.'

        contentlab._chat = fake_chat
        meta, source = contentlab.social_metadata("topic", "script", "youtube_shorts")
        self.assertEqual(source, "llm")
        self.assertEqual(meta["title"], "T2")
        self.assertEqual(meta["hashtags"], ["#x"])

    def test_script_llm_failure_falls_back(self):
        self.old_chat = contentlab._chat

        def boom(prompt, timeout=20):
            raise RuntimeError("provider down")

        contentlab._chat = boom
        script, source = contentlab.generate_script("topic x")
        self.assertEqual(source, "llm_fallback")
        self.assertIn("topic x", script)

    def test_terms_via_mocked_chat(self):
        self.old_chat = contentlab._chat

        def fake_chat(prompt, timeout=20):
            return '["drone flight", "drone closeup"]'

        contentlab._chat = fake_chat
        terms, source = contentlab.stock_terms("drones", "flight\ncloseup", 5)
        self.assertEqual(source, "llm")
        self.assertEqual(terms, ["drone flight", "drone closeup"])


if __name__ == "__main__":
    unittest.main()
