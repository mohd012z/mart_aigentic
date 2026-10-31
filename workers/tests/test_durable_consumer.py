import asyncio
import json
import unittest
from workers.durable_consumer import claim,complete,fail,run_once,MAX_ATTEMPTS

class FakeDB:
 def __init__(self,rows=None):self.rows=rows or [];self.calls=[]
 async def query(self,sql,params=()):
  self.calls.append((sql,params))
  if "RETURNING" in sql and "attempts=attempts+1" in sql:return self.rows[:1]
  return [{"update_id":params[0]}]

class ConsumerTests(unittest.IsolatedAsyncioTestCase):
 async def test_empty_queue(self):
  self.assertIsNone(await claim(FakeDB(),now=100))
 async def test_claim_sets_lease(self):
  db=FakeDB([{"update_id":1,"payload":"{}","attempts":1,"worker_id":"a"}])
  await claim(db,now=100,worker_id="a")
  self.assertEqual(db.calls[0][1],(220,"a",100,MAX_ATTEMPTS))
 async def test_retry_backoff(self):
  db=FakeDB();await fail(db,{"update_id":1,"worker_id":"a","attempts":2},now=100)
  self.assertEqual(db.calls[0][1][2],"pending")
  self.assertEqual(db.calls[0][1][3],104)
 async def test_dead_letter(self):
  db=FakeDB();await fail(db,{"update_id":1,"worker_id":"a","attempts":5},now=100)
  self.assertEqual(db.calls[0][1][2],"dead")
 async def test_successful_handler(self):
  db=FakeDB([{"update_id":1,"payload":json.dumps({"update_id":1}),"attempts":1,"worker_id":"a"}])
  seen=[]
  async def handler(update):seen.append(update["update_id"])
  self.assertEqual(await run_once(db,handler),"completed")
  self.assertEqual(seen,[1])
 async def test_handler_failure(self):
  db=FakeDB([{"update_id":1,"payload":"{}","attempts":1,"worker_id":"a"}])
  async def handler(update):raise RuntimeError("failure")
  self.assertEqual(await run_once(db,handler),"retry")
  self.assertIn("last_error_code",db.calls[-1][0])

if __name__=="__main__":unittest.main()
