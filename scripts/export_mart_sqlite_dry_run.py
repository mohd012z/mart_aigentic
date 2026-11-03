"""Read-only SQLite inventory and consistent backup; never uploads credentials or records."""
import argparse
import json
import os
import sqlite3
from pathlib import Path

TABLES=("campaigns","sessions","updates")
def inspect(source,backup=None):
    source=Path(source)
    if not source.is_file():raise FileNotFoundError(source)
    uri=f"file:{source.resolve()}?mode=ro"
    with sqlite3.connect(uri,uri=True) as conn:
        existing={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts={name:conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in TABLES if name in existing}
        if backup:
            dest=Path(backup)
            if dest.exists():raise FileExistsError(dest)
            dest.parent.mkdir(parents=True,exist_ok=True)
            with sqlite3.connect(str(dest)) as output:conn.backup(output)
            with sqlite3.connect(f"file:{dest.resolve()}?mode=ro",uri=True) as check:
                for name,n in counts.items():
                    if check.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]!=n:
                        raise RuntimeError("Backup row-count mismatch: "+name)
    return {"source":str(source),"tables":counts,"backup":str(backup) if backup else None,"mode":"read_only"}
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--backup")
    args=parser.parse_args()
    print(json.dumps(inspect(args.source,args.backup),sort_keys=True))
