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
 async def test_migration_idempotent(self):
  w.migrate()
  w.migrate()
  with campaigns.conn() as c:
   cols={row[1] for row in c.execute("PRAGMA table_info(campaigns)")}
  self.assertTrue({"attempts","available_at","lease_until","notified"}.issubset(cols))
 async def test_notification_cycle_failure_does_not_undo_campaign(self):
  cid=campaigns.create(12,"earbuds")
  with patch.object(w,"research",AsyncMock(return_value="Research: earbuds")),patch.object(w,"deliver_pending",AsyncMock(side_effect=RuntimeError("offline"))):
   self.assertTrue(await w.run_once())
  self.assertEqual(campaigns.get(cid,12)[0],"review")
 async def test_stale_lease_cannot_overwrite_reclaimed_job(self):
  cid=campaigns.create(12,"earbuds")
  old=w.claim()
  self.assertIsNotNone(old)
  with campaigns.conn() as c:
   c.execute("UPDATE campaigns SET lease_until=0 WHERE id=?",(cid,))
   c.commit()
  new=w.claim()
  self.assertNotEqual(old[4],new[4])
  self.assertFalse(w.complete(cid,"stale output",owner=old[4]))
  self.assertTrue(w.complete(cid,"fresh output",owner=new[4]))
  self.assertEqual(campaigns.get(cid,12),("review","fresh output"))
 async def test_completion_requires_owner(self):
  cid=campaigns.create(12,"earbuds")
  w.claim()
  with self.assertRaises(ValueError):w.complete(cid,"unsafe")
if __name__=="__main__":unittest.main()
