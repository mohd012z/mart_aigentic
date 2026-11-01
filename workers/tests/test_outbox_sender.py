import unittest
import httpx
from workers import outbox_sender as o

class FakeDB:
 def __init__(self,claim=None,transition_accepted=True):self.claim_row=claim;self.calls=[];self.transition_accepted=transition_accepted
 async def query(self,sql,params=()):
  self.calls.append((sql,params))
  if 'attempts=attempts+1' in sql:return [self.claim_row] if self.claim_row else []
  if "state='sending' AND lease_until>=?6" in sql and not self.transition_accepted:return []
  return [{'id':params[0]}] if params else []

class FakeClient:
 def __init__(self,response=None,error=None):self.response=response;self.error=error;self.calls=0
 async def post(self,*args,**kwargs):
  self.calls+=1
  if self.error:raise self.error
  return self.response

def row(attempts=1):
 return dict(id='u:1:sendMessage',chat_id=1,method='sendMessage',payload='{"chat_id":1,"text":"hi"}',attempts=attempts,worker_id='owner')

class OutboxTests(unittest.IsolatedAsyncioTestCase):
 async def test_claim_uses_lease_and_attempt_cap(self):
  db=FakeDB(row());await o.claim(db,now=100,owner='owner')
  self.assertEqual(db.calls[0][1],(190,'owner',100,5))
 async def test_transition_rejects_expired_lease(self):
  db=FakeDB(row());await o.transition(db,row(),'sent',now=100)
  self.assertIn('lease_until>=?6',db.calls[-1][0])
 async def test_timeout_quarantined(self):
  db=FakeDB(row());client=FakeClient(error=httpx.ReadTimeout('timeout'))
  self.assertEqual(await o.deliver_once(db,'dummy',client),'uncertain')
  self.assertEqual(client.calls,1)
  self.assertIn('worker_id=?2',db.calls[-1][0])
  self.assertEqual(db.calls[-1][1][2],'uncertain')
 async def test_success_marked_sent(self):
  db=FakeDB(row());response=httpx.Response(200,json={'ok':True,'result':{'message_id':77}})
  self.assertEqual(await o.deliver_once(db,'dummy',FakeClient(response)),'sent')
  self.assertEqual(db.calls[-1][1][3],77)
 async def test_rate_limit_quarantined(self):
  db=FakeDB(row());response=httpx.Response(429,json={'ok':False})
  self.assertEqual(await o.deliver_once(db,'dummy',FakeClient(response)),'uncertain')
 async def test_expired_lease_quarantined(self):
  db=FakeDB();await o.quarantine_expired(db,now=200)
  self.assertIn("state='uncertain'",db.calls[-1][0])
 async def test_reconciliation_requires_decision(self):
  with self.assertRaises(ValueError):await o.reconcile(FakeDB(),'id','pending')
 async def test_lost_lease_after_telegram_success_not_reported_sent(self):
  db=FakeDB(row(),transition_accepted=False)
  response=httpx.Response(200,json={'ok':True,'result':{'message_id':77}})
  self.assertEqual(await o.deliver_once(db,'dummy',FakeClient(response)),'uncertain')
 async def test_malformed_json_payload_quarantined_without_network_send(self):
  bad=row();bad['payload']='{'
  client=FakeClient()
  self.assertEqual(await o.deliver_once(FakeDB(bad),'dummy',client),'dead')
  self.assertEqual(client.calls,0)
 async def test_unexpected_telegram_response_type_quarantined(self):
  response=httpx.Response(200,json=['unexpected'])
  self.assertEqual(await o.deliver_once(FakeDB(row()),'dummy',FakeClient(response)),'uncertain')
 async def test_unexpected_success_result_type_quarantined(self):
  response=httpx.Response(200,json={'ok':True,'result':'unexpected'})
  self.assertEqual(await o.deliver_once(FakeDB(row()),'dummy',FakeClient(response)),'uncertain')
 async def test_callback_boolean_success_is_persisted_as_sent(self):
  callback=row();callback['method']='answerCallbackQuery';callback['payload']='{"callback_query_id":"q1"}'
  db=FakeDB(callback)
  response=httpx.Response(200,json={'ok':True,'result':True})
  self.assertEqual(await o.deliver_once(db,'dummy',FakeClient(response)),'sent')
  self.assertIsNone(db.calls[-1][1][3])
 async def test_callback_object_result_is_uncertain(self):
  callback=row();callback['method']='answerCallbackQuery';callback['payload']='{"callback_query_id":"q1"}'
  response=httpx.Response(200,json={'ok':True,'result':{'message_id':77}})
  self.assertEqual(await o.deliver_once(FakeDB(callback),'dummy',FakeClient(response)),'uncertain')
 async def test_message_missing_message_id_is_uncertain(self):
  response=httpx.Response(200,json={'ok':True,'result':{}})
  self.assertEqual(await o.deliver_once(FakeDB(row()),'dummy',FakeClient(response)),'uncertain')
 async def test_callback_lost_lease_is_uncertain(self):
  callback=row();callback['method']='answerCallbackQuery';callback['payload']='{"callback_query_id":"q1"}'
  response=httpx.Response(200,json={'ok':True,'result':True})
  self.assertEqual(await o.deliver_once(FakeDB(callback,transition_accepted=False),'dummy',FakeClient(response)),'uncertain')
if __name__=='__main__':unittest.main()
