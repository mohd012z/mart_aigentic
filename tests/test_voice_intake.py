import unittest
from voice_intake import parse_command,VoiceError
class VoiceTests(unittest.TestCase):
 def test_campaign(self):self.assertEqual(parse_command("Create campaign wireless earbuds"),("campaign","wireless earbuds"))
 def test_research_malay(self):self.assertEqual(parse_command("Cari headphones"),("research","headphones"))
 def test_unknown_requires_confirmation(self):self.assertEqual(parse_command("publish this immediately"),("confirm","publish this immediately"))
 def test_length_limit(self):
  with self.assertRaises(VoiceError):parse_command("x"*501)
if __name__=="__main__":unittest.main()
