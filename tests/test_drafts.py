"""Offline tests for the deterministic marketing content generators."""
import unittest
from drafts import (marketing_plan, ads_draft, social_draft, video_draft,
                    create_draft)


class DraftGeneratorTests(unittest.TestCase):
    def test_marketing_plan_is_structured_and_topic_specific(self):
        out = marketing_plan("forex copy trading for Malaysian beginners")
        self.assertIn("MARKETING PLAN", out)
        for section in ("OBJECTIVE", "AUDIENCE", "CHANNELS", "FUNNEL",
                        "BUDGET", "KPI", "30-DAY CALENDAR"):
            self.assertIn(section, out)
        self.assertIn("forex copy trading", out)
        self.assertLessEqual(len(out), 3900)

    def test_ads_has_headlines_and_platforms(self):
        out = ads_draft("binary options trading app")
        self.assertIn("AD COPY", out)
        self.assertIn("HEADLINES", out)
        for platform in ("Meta", "Google", "TikTok"):
            self.assertIn(platform, out)
        self.assertIn("binary options trading app", out)

    def test_social_has_calendar_and_bilingual(self):
        out = social_draft("gold trading signals")
        self.assertIn("SOCIAL CONTENT", out)
        self.assertIn("7-DAY CALENDAR", out)
        self.assertIn("MALAY", out)
        self.assertIn("gold trading signals", out)

    def test_video_has_cutdowns_and_cta(self):
        out = video_draft("mt5 for beginners")
        self.assertIn("VIDEO SCRIPT", out)
        self.assertIn("30-SECOND CUT", out)
        self.assertIn("60-SECOND CUT", out)
        self.assertIn("CTA", out)
        self.assertIn("mt5 for beginners", out)

    def test_all_generators_are_topic_specific(self):
        for gen in (marketing_plan, ads_draft, social_draft, video_draft):
            a = gen("alpha product")
            b = gen("beta service")
            self.assertNotEqual(a, b, f"{gen.__name__} ignored its topic")
            self.assertIn("alpha product", a)
            self.assertIn("beta service", b)

    def test_create_draft_dispatches_and_falls_back(self):
        self.assertIn("MARKETING PLAN", create_draft("marketing", "x"))
        self.assertIn("AD COPY", create_draft("ads", "x"))
        self.assertIn("SOCIAL CONTENT", create_draft("social", "x"))
        self.assertIn("VIDEO SCRIPT", create_draft("video", "x"))
        self.assertIn("DISCLOSE", create_draft("unknown_kind", "x").upper())

    def test_whitespace_and_long_topic_safe(self):
        self.assertNotIn("\n\n\n", marketing_plan("  spaced   out   topic  "))
        self.assertLessEqual(len(create_draft("marketing", "x" * 500)), 3900)


if __name__ == "__main__":
    unittest.main()
