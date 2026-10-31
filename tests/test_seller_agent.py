import unittest
from seller_agent import parse_products, summarize, listing_advice

class SellerAgentTests(unittest.TestCase):
    def test_csv_summary(self):
        data = b"Product Name,Stock,Price\nWidget,2,10.50\nCable,8,4.00\n"
        report = summarize(parse_products(data))
        self.assertEqual(report["products"], 2)
        self.assertEqual(report["units"], 10)
        self.assertEqual(report["low_stock_count"], 1)
        self.assertEqual(report["inventory_list_price_value"], "53.00")
        self.assertFalse(report["live"])

    def test_bad_stock_rejected(self):
        with self.assertRaises(ValueError):
            parse_products(b"Name,Stock,Price\nWidget,-1,3\n")

    def test_bad_price_rejected(self):
        with self.assertRaises(ValueError):
            parse_products(b"Name,Stock,Price\nWidget,1,NaN\n")

    def test_missing_header_rejected(self):
        with self.assertRaises(ValueError):
            parse_products(b"Item,Count\nWidget,2\n")

    def test_listing_requires_approval(self):
        self.assertFalse(listing_advice("USB cable")["auto_publish"])

if __name__ == "__main__":
    unittest.main()
