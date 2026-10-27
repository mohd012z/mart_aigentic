import os
import tempfile
import unittest
from observability import record, summary, report

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
    def tearDown(self):
        self.tmp.cleanup()
    def test_empty(self):
        self.assertEqual(summary(self.path)["calls"], 0)
    def test_success_and_failure(self):
        record("research", cost_usd=0.01, path=self.path)
        record("research", status="failed", error_type="Timeout", path=self.path)
        s = summary(self.path)
        self.assertEqual((s["calls"], s["success"], s["failures"]), (2,1,1))
        self.assertEqual(s["unknown_cost_calls"], 1)
        self.assertAlmostEqual(s["known_cost_usd"], 0.01)
    def test_negative_cost_rejected(self):
        with self.assertRaises(ValueError):
            record("research", cost_usd=-1, path=self.path)
    def test_report_coverage(self):
        self.assertIn("Unknown cost is not treated as free", report(self.path))
if __name__ == "__main__":
    unittest.main()
