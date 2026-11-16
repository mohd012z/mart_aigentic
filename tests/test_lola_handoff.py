import unittest
from lola_handoff import sign_handoff, verify_handoff

SECRET = "s" * 40
PAYLOAD = {"bot_username": "@mart_aigenticbot", "user_id": 42,
           "chat_id": 42, "update_id": 7, "text": "Hello LOLA"}


class HandoffTests(unittest.TestCase):
    def test_roundtrip(self):
        body, sig = sign_handoff(PAYLOAD, SECRET, now=1000)
        self.assertEqual(verify_handoff(body, sig, SECRET, now=1001)["text"], "Hello LOLA")

    def test_tamper_denied(self):
        body, sig = sign_handoff(PAYLOAD, SECRET, now=1000)
        with self.assertRaises(PermissionError):
            verify_handoff(body.replace(b"Hello", b"Other"), sig, SECRET, now=1001)

    def test_expired_denied(self):
        body, sig = sign_handoff(PAYLOAD, SECRET, now=1000)
        with self.assertRaises(PermissionError):
            verify_handoff(body, sig, SECRET, now=1301)

    def test_wrong_bot_denied(self):
        body, sig = sign_handoff({**PAYLOAD, "bot_username": "anotherbot"}, SECRET, now=1000)
        with self.assertRaises(PermissionError):
            verify_handoff(body, sig, SECRET, now=1001)

    def test_execution_denied(self):
        body, sig = sign_handoff({**PAYLOAD, "requires_execution": True}, SECRET, now=1000)
        with self.assertRaises(PermissionError):
            verify_handoff(body, sig, SECRET, now=1001)

    def test_short_secret_denied(self):
        with self.assertRaises(ValueError):
            sign_handoff(PAYLOAD, "short", now=1000)


if __name__ == "__main__":
    unittest.main()
