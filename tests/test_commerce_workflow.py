import unittest
from commerce_workflow import new_campaign, publish

class CommerceWorkflowTests(unittest.TestCase):
    def test_approval_path(self):
        c = new_campaign(123, "USB-C cable", ["facebook", "instagram", "threads"])
        for state in ("review", "approved", "ready"):
            self.assertEqual(c.transition(state, 123), state)
        self.assertEqual(len(c.history), 3)

    def test_other_user_cannot_approve(self):
        c = new_campaign(123, "Cable", ["tiktok"])
        with self.assertRaises(PermissionError):
            c.transition("review", 456)

    def test_no_skipped_approval(self):
        c = new_campaign(123, "Cable", ["shopee"])
        with self.assertRaises(ValueError):
            c.transition("ready", 123)

    def test_invalid_platform(self):
        with self.assertRaises(ValueError):
            new_campaign(123, "Cable", ["invalid"])

    def test_publish_disabled(self):
        c = new_campaign(123, "Cable", ["facebook"])
        with self.assertRaises(PermissionError):
            publish(c)

if __name__ == "__main__":
    unittest.main()
