import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.mart_migration_manifest import build_manifest,compare

class ManifestTests(unittest.TestCase):
 def test_deterministic_manifest_and_mismatch(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'data.sqlite3'
   with sqlite3.connect(path) as conn:
    conn.execute('CREATE TABLE updates(id INTEGER PRIMARY KEY)')
    conn.execute('INSERT INTO updates VALUES (1)')
   first=build_manifest(path);second=build_manifest(path)
   self.assertEqual(first,second)
   self.assertTrue(compare(first,second)['matched'])
   with sqlite3.connect(path) as conn:conn.execute('INSERT INTO updates VALUES (2)')
   changed=build_manifest(path)
   self.assertFalse(compare(first,changed)['matched'])
 def test_missing_source(self):
  with self.assertRaises(FileNotFoundError):build_manifest('/nonexistent/mart-migration.sqlite')
if __name__=='__main__':unittest.main()
