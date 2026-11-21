import unittest
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch
from mart_engine import score, unique_results, signal_signals, recommend, affiliate_brief
import affiliate_catalog

class EngineTests(unittest.TestCase):
    def test_score_bounds(self):
        self.assertEqual(score({"demand": 5, "competition": 5, "monetization": 5, "evidence": 5}), 100)
        self.assertEqual(score({}), 0)
    def test_duplicate_urls(self):
        items = [{"url": "https://example.com/a"}, {"url": "https://example.com/a/"}, {"url": "http://bad.test/x"}, {"url": "https://other.com/b"}]
        self.assertEqual(len(unique_results(items)), 2)
    def test_no_unverified_http(self):
        self.assertEqual(unique_results([{"url": "http://example.com"}]), [])

    def _results(self):
        return [
            {"title": "Top <b>10</b> alternatives and competitors", "url": "https://a.example/list", "description": "Compare competitors, market share and alternative options"},
            {"title": "Demand and growth trends", "url": "https://b.example/trends", "description": "Search for demand, buy trends and growth data"},
            {"title": "Pricing and commission", "url": "https://c.example/pricing", "description": "Price data, commission rates and revenue margins"},
            {"title": "Buying guide", "url": "https://d.example/guide", "description": "Popular choices and purchasing considerations"},
        ]

    def test_signal_signals_reproducible(self):
        signals = signal_signals(self._results())
        self.assertEqual(set(signals), {"demand", "competition", "monetization", "evidence"})
        for value in signals.values():
            self.assertTrue(0 <= value <= 5)
        self.assertEqual(signals["evidence"], 4)

    def test_recommend_differs_from_research_and_uses_score(self):
        with patch.object(mart_engine_mod(), "fetch_results", new=AsyncMock(return_value=(self._results(), None))), \
             patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "dummy"}):
            out = asyncio.run(recommend("gadgets"))
        self.assertIn("Recommendation brief", out)
        self.assertIn("signal score", out.lower())
        self.assertNotIn("Evidence sources:", out)

    def test_recommend_reports_missing_provider(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAVE_SEARCH_API_KEY", None)
            self.assertTrue(asyncio.run(recommend("gadgets")).startswith("Research provider not configured"))

    def test_affiliate_brief_lists_verified_offer_and_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "offers.sqlite")
            affiliate_catalog.add_offer(db, "Example", "Sample Product",
                "https://example.org/product", "https://example.org/terms", "2026-11-01", "8%")
            with patch.object(mart_engine_mod(), "fetch_results", new=AsyncMock(return_value=(self._results(), None))):
                out = asyncio.run(affiliate_brief("sample product", db))
            self.assertIn("Verified offers", out)
            self.assertIn("https://example.org/product", out)
            self.assertIn("Affiliate disclosure:", out)
            self.assertIn("Market evidence:", out)

    def test_affiliate_brief_no_catalog_still_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "empty.sqlite")
            with patch.object(mart_engine_mod(), "fetch_results", new=AsyncMock(return_value=(self._results(), None))):
                out = asyncio.run(affiliate_brief("anything", db))
            self.assertNotIn("Verified offers", out)
            self.assertIn("Market evidence:", out)
            self.assertIn("Affiliate disclosure:", out)

def mart_engine_mod():
    import mart_engine
    return mart_engine

if __name__ == "__main__":
    unittest.main()
