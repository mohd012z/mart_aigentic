import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.export_mart_sqlite_dry_run import inspect

class DryRunTests(unittest.TestCase):
 def test_backup_counts_and_original_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/"mart.db";backup=Path(d)/"backup.db"
   with sqlite3.connect(src) as c:
    c.execute("CREATE TABLE updates(id INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO updates VALUES(42)")
   result=inspect(src,backup)
   self.assertEqual(result["tables"],{"updates":1})
   self.assertEqual(inspect(backup)["tables"],{"updates":1})
   with self.assertRaises(FileExistsError):inspect(src,backup)

if __name__=="__main__":unittest.main()
