import unittest
from scripts.diagnose_telegram import summarize

class TelegramDiagnosticsTests(unittest.TestCase):
    def test_bot_identity(self):
        self.assertEqual(summarize("getMe", {"ok": True, "result": {"username": "mart_test", "is_bot": True}})["username"], "mart_test")

    def test_webhook_redacts_url(self):
        data = summarize("getWebhookInfo", {"ok": True, "result": {
            "url": "https://private.example/secret-path", "pending_update_count": 3,
            "last_error_message": "Connection refused"}})
        self.assertTrue(data["webhook_configured"])
        self.assertEqual(data["pending_update_count"], 3)
        self.assertNotIn("private.example", repr(data))

    def test_commands(self):
        data = summarize("getMyCommands", {"ok": True, "result": [{"command": "start"}]})
        self.assertEqual(data["commands"], ["start"])

    def test_failed_api(self):
        data = summarize("getMe", {"ok": False, "error_code": 401, "description": "secret"})
        self.assertEqual(data, {"method": "getMe", "ok": False, "error_code": 401})

if __name__ == "__main__":
    unittest.main()
