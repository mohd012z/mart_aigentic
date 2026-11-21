import unittest
from scripts.diagnose_telegram import classify_error, summarize, EXPECTED_COMMANDS


class DiagnosticTests(unittest.TestCase):
    def test_identity_match(self):
        self.assertTrue(summarize("getMe", {"ok": True, "result": {"username": "mart_aigenticbot", "is_bot": True}})["username_matches_expected"])

    def test_wrong_identity(self):
        self.assertFalse(summarize("getMe", {"ok": True, "result": {"username": "other_bot", "is_bot": True}})["username_matches_expected"])

    def test_no_webhook(self):
        result = summarize("getWebhookInfo", {"ok": True, "result": {"url": "", "pending_update_count": 3}})
        self.assertFalse(result["webhook_configured"])
        self.assertEqual(result["pending_update_count"], 3)

    def test_secret_error_redaction(self):
        message = "Wrong response from https://private.example/path?secret=abc: 403 Forbidden"
        result = summarize("getWebhookInfo", {"ok": True, "result": {"url": "https://private.example/path", "last_error_message": message}})
        self.assertEqual(result["delivery_error_category"], "authentication_or_forbidden")
        self.assertNotIn("private.example", str(result))
        self.assertNotIn("abc", str(result))

    def test_missing_message_updates(self):
        result = summarize("getWebhookInfo", {"ok": True, "result": {"allowed_updates": ["callback_query"]}})
        self.assertFalse(result["message_updates_allowed"])

    def test_default_message_updates(self):
        result = summarize("getWebhookInfo", {"ok": True, "result": {}})
        self.assertTrue(result["message_updates_allowed"])

    def test_command_parity(self):
        result = summarize("getMyCommands", {"ok": True, "result": [{"command": c} for c in EXPECTED_COMMANDS]})
        self.assertEqual(result["missing_commands"], [])
        self.assertEqual(result["unexpected_commands"], [])

    def test_missing_commands(self):
        result = summarize("getMyCommands", {"ok": True, "result": [{"command": "start"}]})
        self.assertEqual(len(result["missing_commands"]), 14)

    def test_malformed_payload(self):
        self.assertFalse(summarize("getWebhookInfo", {"ok": True, "result": []})["ok"])

    def test_error_categories(self):
        for msg, expected in [("connection timed out", "timeout"), ("SSL certificate failed", "tls_error"), ("502 Bad Gateway", "upstream_unavailable"), ("404 Not Found", "not_found"), ("network connection refused", "connection_error"), ("unexpected issue", "other")]:
            self.assertEqual(classify_error(msg), expected)


if __name__ == "__main__":
    unittest.main()
