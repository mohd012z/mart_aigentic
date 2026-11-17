import sqlite3
import unittest
from pathlib import Path
from workers.transactional_staging import stage_command,initialize_sqlite

ROOT=Path(__file__).resolve().parents[1]
class TransactionTests(unittest.TestCase):
 def setUp(self):
  self.conn=sqlite3.connect(':memory:')
  initialize_sqlite(self.conn,(ROOT/'schema.sql').read_text(),(ROOT/'outbox.sql').read_text())
  self.conn.execute("INSERT INTO telegram_updates(update_id,payload,status,worker_id,lease_until) VALUES(1,'{}','processing','owner',9999999999)")
 def tearDown(self):self.conn.close()
 def test_atomic_replay(self):
  payload={'chat_id':12,'text':'Hello'}
  self.assertTrue(stage_command(self.conn,1,12,'sendMessage',payload,owner='owner',now=100))
  self.assertFalse(stage_command(self.conn,1,12,'sendMessage',payload,owner='owner',now=100))
  self.assertEqual(self.conn.execute('SELECT count(*) FROM telegram_outbox').fetchone()[0],1)
  self.assertEqual(self.conn.execute('SELECT status FROM telegram_updates').fetchone()[0],'completed')
 def test_stale_owner_cannot_stage(self):
  self.assertFalse(stage_command(self.conn,1,12,'sendMessage',{'text':'x'},owner='stale',now=100))
  self.assertEqual(self.conn.execute('SELECT count(*) FROM telegram_outbox').fetchone()[0],0)
 def test_expired_lease_cannot_stage(self):
  self.assertFalse(stage_command(self.conn,1,12,'sendMessage',{'text':'x'},owner='owner',now=99999999999))
  self.assertEqual(self.conn.execute('SELECT status FROM telegram_updates').fetchone()[0],'processing')
 def test_rollback_invalid_method(self):
  with self.assertRaises(ValueError):stage_command(self.conn,1,12,'unknown',{},owner='owner',now=100)
  self.assertEqual(self.conn.execute('SELECT count(*) FROM telegram_outbox').fetchone()[0],0)
  self.assertEqual(self.conn.execute('SELECT status FROM telegram_updates').fetchone()[0],'processing')
if __name__=='__main__':unittest.main()
