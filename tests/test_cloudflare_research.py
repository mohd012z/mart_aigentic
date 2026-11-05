import os
import unittest
from unittest.mock import patch
import httpx
import cloudflare_research as bridge


class CloudflareResearchTests(unittest.IsolatedAsyncioTestCase):
    def test_configuration_rejects_insecure_endpoints(self):
        for url in ("http://example.com", "https://user:pass@example.com", "https://example.com?token=abc"):
            with patch.dict(os.environ, {"MART_RESEARCH_WORKER_URL": url, "MART_INTERNAL_KEY": "secret"}):
                self.assertIsNone(bridge.configuration())

    def test_deterministic_job_id(self):
        self.assertEqual(bridge.job_id(123, 5, "/research"), bridge.job_id(123, 5, "/research"))
        self.assertNotEqual(bridge.job_id(123, 5, "/research"), bridge.job_id(124, 5, "/research"))

    async def test_enqueue_auth_and_payload(self):
        def handler(request):
            self.assertEqual(request.headers["authorization"], "Bearer secret")
            self.assertTrue(request.url.path.endswith("/enqueue"))
            return httpx.Response(202, json={"ok": True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch.dict(os.environ, {"MART_RESEARCH_WORKER_URL": "https://research.example", "MART_INTERNAL_KEY": "secret"}):
                self.assertEqual(len(await bridge.enqueue(1, 123, "Product research", "/research", client)), 40)

    async def test_disabled_no_network(self):
        with patch.dict(os.environ, {"MART_RESEARCH_WORKER_URL": "", "MART_INTERNAL_KEY": ""}):
            self.assertIsNone(await bridge.enqueue(1, 123, "Research topic", "/research"))


if __name__ == "__main__":
    unittest.main()
