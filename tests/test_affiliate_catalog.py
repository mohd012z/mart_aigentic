import os
import tempfile
import unittest
from affiliate_catalog import add_offer, list_offers, validate_url

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=os.path.join(self.tmp.name,"offers.sqlite")
    def tearDown(self):
        self.tmp.cleanup()
    def test_offer_has_provenance_and_disclosure(self):
        add_offer(self.db,"Example","Sample","https://example.org/product",
                  "https://example.org/terms","2026-10-27")
        item=list_offers(self.db)[0]
        self.assertIn("commission",item["disclosure"])
        self.assertEqual(item["source_url"],"https://example.org/terms")
        self.assertIsNone(item["commission_text"])
    def test_reject_http_and_local(self):
        for url in ("http://example.org","https://localhost/path","https://x.local/"):
            with self.assertRaises(ValueError):
                validate_url(url)
    def test_no_fabricated_offers(self):
        self.assertEqual(list_offers(self.db),[])
    def test_unique_offer(self):
        args=(self.db,"Example","Sample","https://example.org/product",
              "https://example.org/terms","2026-10-27")
        add_offer(*args)
        with self.assertRaises(Exception):
            add_offer(*args)
if __name__=="__main__":
    unittest.main()
