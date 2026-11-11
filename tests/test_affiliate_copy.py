import os
import tempfile
import unittest

class AffiliateCopyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import campaigns
        campaigns.DB = os.path.join(self.tmp.name, "test.sqlite3")
        import affiliate_copy
        self.a = affiliate_copy

    def tearDown(self):
        self.tmp.cleanup()

    def test_ten_variants_and_history(self):
        ident, variants = self.a.generate(123, "Reusable water bottle")
        self.assertEqual(len(variants), 10)
        self.assertEqual(len(set(variants)), 10)
        self.assertEqual(self.a.draft(123, ident), variants)
        self.assertIsNone(self.a.draft(999, ident))
        self.assertIn("Reusable water bottle", self.a.history(123))

    def test_language(self):
        self.a.set_language(123, "en")
        _, variants = self.a.generate(123, "Notebook")
        self.assertIn("Affiliate disclosure", variants[0])
        with self.assertRaises(ValueError):
            self.a.set_language(123, "xx")

    def test_product_validation(self):
        self.assertIsNotNone(self.a.valid_product("https://shopee.com.my/item/123"))
        for bad in ("", "http://shopee.com.my/item", "https://evil.example/",
                    "https://shopee.com.my.evil.example/item",
                    "https://user:pass@shopee.com.my/item", "hello\x00world"):
            self.assertIsNone(self.a.valid_product(bad), bad)

    def test_prompt_persistence(self):
        self.a.set_guidance(123, "Use neutral language")
        self.assertEqual(self.a.settings(123)[1], "Use neutral language")
        with self.assertRaises(ValueError):
            self.a.set_guidance(123, "x" * 801)

if __name__ == "__main__":
    unittest.main()
