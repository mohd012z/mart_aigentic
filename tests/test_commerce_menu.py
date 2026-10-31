import unittest
from telegram_ui import commerce_keyboard, commerce_page

class CommerceMenuTests(unittest.TestCase):
    def test_home_has_all_platforms(self):
        data = [b["callback_data"] for row in commerce_keyboard()["inline_keyboard"] for b in row]
        for name in ("shopee", "facebook", "instagram", "threads", "tiktok", "tiktok_shop"):
            self.assertIn("commerce:" + name, data)

    def test_platform_has_draft_and_back(self):
        data = [b["callback_data"] for row in commerce_keyboard("instagram")["inline_keyboard"] for b in row]
        self.assertIn("commerce:draft:instagram", data)
        self.assertIn("commerce:home", data)

    def test_callback_data_size(self):
        for page in ("home", "shopee", "facebook", "instagram", "threads", "tiktok", "tiktok_shop"):
            for row in commerce_keyboard(page)["inline_keyboard"]:
                for button in row:
                    self.assertLessEqual(len(button["callback_data"].encode("utf-8")), 64)

    def test_bad_page_rejected(self):
        with self.assertRaises(ValueError):
            commerce_page("unknown")

if __name__ == "__main__":
    unittest.main()
