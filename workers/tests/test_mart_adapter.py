import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import campaigns
from workers.mart_adapter import deliver_update

class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.original_db=campaigns.DB
  campaigns.DB=os.path.join(self.tmp.name,"mart.sqlite3")
  self.env=patch.dict(os.environ,{"TELEGRAM_WEBHOOK_SECRET":"test-secret"})
  self.env.start()
 async def asyncTearDown(self):
  self.env.stop()
  campaigns.DB=self.original_db
  self.tmp.cleanup()
 async def test_start_reply_mocked(self):
  payload={"update_id":987651,"message":{"chat":{"id":101,"type":"private"},"from":{"id":101},"text":"/start"}}
  with patch("app.send_message",new_callable=AsyncMock) as send:
   result=await deliver_update(payload,secret="test-secret")
   self.assertTrue(result["ok"])
   send.assert_awaited_once()
 async def test_wrong_secret_rejected(self):
  with self.assertRaises(Exception):
   await deliver_update({"update_id":987652},secret="wrong")
if __name__=="__main__":unittest.main()
