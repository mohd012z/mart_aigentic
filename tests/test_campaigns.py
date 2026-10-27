import os,tempfile,unittest
import campaigns
class CampaignTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=campaigns.DB;campaigns.DB=os.path.join(self.tmp.name,"test.db")
 def tearDown(self):
  campaigns.DB=self.old;self.tmp.cleanup()
 def test_dedup(self):
  self.assertTrue(campaigns.accept_update(10));self.assertFalse(campaigns.accept_update(10))
 def test_session(self):
  campaigns.select(1,2,"campaign");self.assertEqual(campaigns.consume(1,2),"campaign");self.assertIsNone(campaigns.consume(1,2))
 def test_lifecycle(self):
  cid=campaigns.create(1,"earbuds");self.assertEqual(campaigns.claim()[0],cid)
  campaigns.finish(cid,"draft");self.assertEqual(campaigns.get(cid,1),("review","draft"))
 def test_isolation(self):
  cid=campaigns.create(1,"earbuds");self.assertIsNone(campaigns.get(cid,2))
 def test_invalid(self):
  with self.assertRaises(ValueError):campaigns.create(1,"")
if __name__=="__main__":unittest.main()
