import os
import unittest
from unittest.mock import AsyncMock,patch
from workers.mart_adapter import deliver_update

class AdapterTests(unittest.IsolatedAsyncioTestCase):
 async def test_start_reply_mocked(self):
  payload={"update_id":987651,"message":{"chat":{"id":101,"type":"private"},"from":{"id":101},"text":"/start"}}
  with patch.dict(os.environ,{"TELEGRAM_WEBHOOK_SECRET":"test-secret"}),patch("app.send_message",new_callable=AsyncMock) as send:
   result=await deliver_update(payload,secret="test-secret")
   self.assertTrue(result["ok"])
   send.assert_awaited_once()
 async def test_wrong_secret_rejected(self):
  with patch.dict(os.environ,{"TELEGRAM_WEBHOOK_SECRET":"test-secret"}):
   with self.assertRaises(Exception):
    await deliver_update({"update_id":987652},secret="wrong")
if __name__=="__main__":unittest.main()
