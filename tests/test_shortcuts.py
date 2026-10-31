import unittest
from unittest.mock import AsyncMock, patch
import os
import tempfile
from fastapi.testclient import TestClient

class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"TELEGRAM_WEBHOOK_SECRET":"local-test-secret",
            "MART_COMMERCE_ENABLED":"1","MART_COMMERCE_ALLOWED_USER_IDS":"123",
            "MART_CAMPAIGN_DB":self.tmp.name+"/mart.sqlite"})
        self.env.start()
        import campaigns
        self.old=campaigns.DB
        campaigns.DB=self.tmp.name+"/mart.sqlite"
        from app import app
        self.client=TestClient(app)
        self.mock=patch("app.send_message",new_callable=AsyncMock)
        self.send=self.mock.start()

    def tearDown(self):
        self.mock.stop()
        import campaigns
        campaigns.DB=self.old
        self.env.stop()
        self.tmp.cleanup()

    def post(self,number,text,uid=123):
        return self.client.post("/telegram/webhook",json={"update_id":number,
            "message":{"chat":{"id":123,"type":"private"},"from":{"id":uid},"text":text}},
            headers={"X-Telegram-Bot-Api-Secret-Token":"local-test-secret"})

    def test_platform_shortcut_opens_menu(self):
        self.assertEqual(self.post(501,"/instagram").status_code,200)
        self.assertIn("Instagram",self.send.await_args.args[1])

    def test_platform_shortcut_drafts(self):
        self.post(502,"/tiktok USB cable")
        self.assertIn("NOT PUBLISHED",self.send.await_args.args[1])

    def test_connections(self):
        self.post(503,"/connections")
        self.assertIn("Connections",self.send.await_args.args[1])

    def test_unauthorized_shortcut(self):
        self.post(504,"/shopee Cable",uid=999)
        self.assertIn("denied",self.send.await_args.args[1])

if __name__=="__main__":
    unittest.main()
