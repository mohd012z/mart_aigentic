import concurrent.futures
import os
import tempfile
import unittest
from pathlib import Path
from workers.sqlite_recovery import connect, ingest, claim, complete_with_outbox, process_once

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=Path(self.tmp.name)/'mart.db'
  self.db=connect(self.path)
 def tearDown(self):
  self.db.close()
  self.tmp.cleanup()
 def test_duplicate_and_atomic_completion(self):
  update={'update_id':1,'message':{'chat':{'id':42},'text':'/help'}}
  self.assertTrue(ingest(self.db,update))
  self.assertFalse(ingest(self.db,update))
  self.assertEqual(process_once(self.db,now=100,owner='a'),'completed')
  self.assertEqual(process_once(self.db,now=100,owner='b'),'idle')
  self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0],1)
 def test_transaction_rollback(self):
  ingest(self.db,{'update_id':2})
  row=claim(self.db,now=100,owner='a')
  with self.assertRaises(ValueError):
   complete_with_outbox(self.db,row,[('sendMessage',1,{'text':'ok'}),('invalid',1,{})],now=100)
  self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0],0)
 def test_stale_lease_fenced(self):
  ingest(self.db,{'update_id':3})
  old=claim(self.db,now=100,owner='old',lease_seconds=10)
  new=claim(self.db,now=111,owner='new')
  with self.assertRaises(RuntimeError):
   complete_with_outbox(self.db,old,[('sendMessage',1,{'text':'old'})],now=111)
  complete_with_outbox(self.db,new,[('sendMessage',1,{'text':'new'})],now=111)
  self.assertEqual(self.db.execute('SELECT COUNT(*) FROM telegram_outbox').fetchone()[0],1)
 def test_concurrent_claims(self):
  for i in range(30):
   ingest(self.db,{'update_id':100+i})
  def worker(i):
   db=connect(self.path)
   try:
    row=claim(db,now=100,owner=str(i))
    return row['update_id'] if row else None
   finally:
    db.close()
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
   ids=list(pool.map(worker,range(30)))
  self.assertEqual(len(set(ids)),30)
  self.assertNotIn(None,ids)
 def test_exhausted_update_does_not_starve(self):
  ingest(self.db,{'update_id':200})
  ingest(self.db,{'update_id':201})
  self.db.execute('UPDATE telegram_updates SET attempts=5 WHERE update_id=200')
  self.assertEqual(claim(self.db,now=100,owner='a')['update_id'],201)
 def test_callback_outbox_intent(self):
  ingest(self.db,{'update_id':300,'callback_query':{'id':'cb'}})
  self.assertEqual(process_once(self.db,now=100,owner='a'),'completed')
  self.assertEqual(self.db.execute('SELECT method FROM telegram_outbox').fetchone()[0],'answerCallbackQuery')
if __name__=='__main__':
 unittest.main()
