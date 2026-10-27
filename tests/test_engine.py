import unittest
from mart_engine import score, unique_results

class EngineTests(unittest.TestCase):
    def test_score_bounds(self):
        self.assertEqual(score({"demand": 5, "competition": 5, "monetization": 5, "evidence": 5}), 100)
        self.assertEqual(score({}), 0)
    def test_duplicate_urls(self):
        items = [{"url": "https://example.com/a"}, {"url": "https://example.com/a/"}, {"url": "http://bad.test/x"}, {"url": "https://other.com/b"}]
        self.assertEqual(len(unique_results(items)), 2)
    def test_no_unverified_http(self):
        self.assertEqual(unique_results([{"url": "http://example.com"}]), [])

if __name__ == "__main__":
    unittest.main()
