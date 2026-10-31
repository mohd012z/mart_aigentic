"""Regression tests for interpreting Telegram diagnostic results safely."""
import unittest
from scripts.diagnose_telegram import summarize

class TelegramDiagnosticContract(unittest.TestCase):
    def test_no_webhook_is_reported_without_failure(self):
        result = summarize("getWebhookInfo", {"ok": True, "result": {
            "url": "", "pending_update_count": 12}})
        self.assertTrue(result["ok"])
        self.assertFalse(result["webhook_configured"])
        self.assertEqual(result["pending_update_count"], 12)

    def test_delivery_error_is_reported_without_leaking_message(self):
        result = summarize("getWebhookInfo", {"ok": True, "result": {
            "url": "https://secret.example/hook", "last_error_message": "403 Forbidden",
            "last_error_date": 1793450000}})
        self.assertTrue(result["has_delivery_error"])
        self.assertEqual(result["last_error_date"], 1793450000)
        self.assertNotIn("secret.example", str(result))
        self.assertNotIn("403 Forbidden", str(result))

    def test_bot_token_rejection_is_nonsecret(self):
        self.assertEqual(summarize("getMe", {"ok": False,
            "error_code": 401, "description": "private token"}), {
            "method": "getMe", "ok": False, "error_code": 401})

if __name__ == "__main__":
    unittest.main()
