import os
import tempfile
import unittest
from unittest.mock import AsyncMock,patch
import campaigns
import campaign_worker as worker

class IntegratedTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.old=campaigns.DB
  campaigns.DB=os.path.join(self.temp.name,"test.sqlite")
 def tearDown(self):
  campaigns.DB=self.old
  self.temp.cleanup()
 async def test_ai_draft_with_evidence(self):
  cid=campaigns.create(100,"headphones")
  with patch.object(worker,"research",AsyncMock(return_value="Research: headphones; evidence https://example.org")),patch.object(worker,"configured",return_value=True),patch.object(worker,"generate",AsyncMock(return_value="Ad: compare headphones.")) as gen,patch.object(worker,"notify",AsyncMock()):
   await worker.run_once()
   self.assertIn("AI CAMPAIGN DRAFT",campaigns.get(cid,100)[1])
   gen.assert_awaited_once()
 async def test_ai_failure_uses_safe_draft(self):
  cid=campaigns.create(100,"headphones")
  with patch.object(worker,"research",AsyncMock(return_value="Research: headphones")),patch.object(worker,"configured",return_value=True),patch.object(worker,"generate",AsyncMock(side_effect=worker.GatewayError("offline"))),patch.object(worker,"notify",AsyncMock()):
   await worker.run_once()
   self.assertEqual(campaigns.get(cid,100)[0],"review")
   self.assertIn("CAMPAIGN DRAFT",campaigns.get(cid,100)[1])
if __name__=="__main__":unittest.main()
