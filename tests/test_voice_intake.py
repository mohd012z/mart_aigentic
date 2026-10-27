import unittest
import os
import httpx
from unittest.mock import patch
from voice_intake import parse_command,VoiceError,transcribe_telegram_voice
class VoiceTests(unittest.TestCase):
 def test_campaign(self):self.assertEqual(parse_command("Create campaign wireless earbuds"),("campaign","wireless earbuds"))
 def test_research_malay(self):self.assertEqual(parse_command("Cari headphones"),("research","headphones"))
 def test_unknown_requires_confirmation(self):self.assertEqual(parse_command("publish this immediately"),("confirm","publish this immediately"))
 def test_length_limit(self):
  with self.assertRaises(VoiceError):parse_command("x"*501)
class VoiceTransportTests(unittest.IsolatedAsyncioTestCase):
 async def test_transcription_success(self):
  def handler(request):
   if request.url.path.endswith("/getFile"):
    return httpx.Response(200,json={"ok":True,"result":{"file_path":"voice/test.oga","file_size":5}})
   if "/file/bot" in request.url.path:
    return httpx.Response(200,content=b"audio")
   return httpx.Response(200,json={"text":"campaign wireless earbuds"})
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
   with patch.dict(os.environ,{"TELEGRAM_BOT_TOKEN":"test","MART_TRANSCRIBE_API_KEY":"test"}):
    self.assertEqual(await transcribe_telegram_voice("file-id",12,client),"campaign wireless earbuds")
 async def test_oversized_file_rejected(self):
  def handler(request):
   return httpx.Response(200,json={"ok":True,"result":{"file_path":"voice/test.oga","file_size":99999999}})
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
   with patch.dict(os.environ,{"TELEGRAM_BOT_TOKEN":"test","MART_TRANSCRIBE_API_KEY":"test"}):
    with self.assertRaises(VoiceError):await transcribe_telegram_voice("file-id",12,client)
 async def test_empty_transcript_rejected(self):
  def handler(request):
   if request.url.path.endswith("/getFile"):
    return httpx.Response(200,json={"ok":True,"result":{"file_path":"voice/test.oga","file_size":5}})
   if "/file/bot" in request.url.path:return httpx.Response(200,content=b"audio")
   return httpx.Response(200,json={"text":""})
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
   with patch.dict(os.environ,{"TELEGRAM_BOT_TOKEN":"test","MART_TRANSCRIBE_API_KEY":"test"}):
    with self.assertRaises(VoiceError):await transcribe_telegram_voice("file-id",12,client)
if __name__=="__main__":unittest.main()
