import os,unittest
from unittest.mock import patch
from ai_gateway import generate,GatewayError
from provider_registry import status
class GatewayTests(unittest.IsolatedAsyncioTestCase):
 async def test_missing_configuration(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(GatewayError):await generate("write a caption")
 async def test_reject_unknown_provider(self):
  with self.assertRaises(GatewayError):await generate("hello","unknown")
 async def test_reject_empty_prompt(self):
  with self.assertRaises(ValueError):await generate(" ")
 async def test_registry_without_credentials(self):
  with patch.dict(os.environ,{},clear=True):
   self.assertFalse(status()["openai_compatible"]["configured"])
if __name__=="__main__":unittest.main()
