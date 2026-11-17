import os
import tempfile
import unittest
from unittest.mock import AsyncMock,patch
import campaigns
import campaign_worker as w

class WorkerTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.old=campaigns.DB
  campaigns.DB=os.path.join(self.temp.name,"db.sqlite")
 def tearDown(self):
  campaigns.DB=self.old
  self.temp.cleanup()
 async def test_complete_and_notify(self):
  cid=campaigns.create(12,"earbuds")
  with patch.object(w,"research",AsyncMock(return_value="Research: earbuds\nEvidence sources: source")),patch.object(w,"notify",AsyncMock()) as notify:
   self.assertTrue(await w.run_once())
   self.assertEqual(campaigns.get(cid,12)[0],"review")
   notify.assert_awaited_once()
 async def test_failed_research_retries(self):
  cid=campaigns.create(12,"earbuds")
  with patch.object(w,"research",AsyncMock(return_value="Research provider not configured")),patch.object(w,"notify",AsyncMock()):
   await w.run_once()
  self.assertEqual(campaigns.get(cid,12)[0],"queued")
 async def test_no_duplicate_delivery_after_success(self):
  cid=campaigns.create(12,"earbuds")
  with patch.object(w,"research",AsyncMock(return_value="Research: earbuds")),patch.object(w,"notify",AsyncMock()) as notify:
   await w.run_once()
   await w.deliver_pending()
   self.assertEqual(notify.await_count,1)
if __name__=="__main__":unittest.main()
