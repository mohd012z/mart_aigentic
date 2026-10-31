import unittest
from social_agent import PLATFORMS, draft, platform_status

class SocialAgentTests(unittest.TestCase):
    def test_all_platforms(self):
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                result = draft(platform, "USB-C cable", "1 metre cable")
                self.assertTrue(result["requires_review"])
                self.assertFalse(result["published"])
                self.assertFalse(result["api_connected"])

    def test_affiliate_disclosure(self):
        self.assertIn("commission", draft("threads", "Cable", affiliate=True)["draft"])

    def test_unknown_platform(self):
        with self.assertRaises(ValueError):
            draft("unknown", "Cable")

    def test_empty_product(self):
        with self.assertRaises(ValueError):
            draft("facebook", "")

    def test_no_live_connections(self):
        self.assertTrue(all(not p["publishing_enabled"] for p in platform_status().values()))

if __name__ == "__main__":
    unittest.main()
