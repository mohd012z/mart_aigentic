"""Offline migration manifest. Does not write D1 or modify original SQLite."""
import hashlib
import json
import sqlite3
from pathlib import Path

TABLES=('campaigns','sessions','updates')
def build_manifest(path):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    with sqlite3.connect(f'file:{path.resolve()}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        existing={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        manifest={'schema_version':1,'tables':{},'mode':'dry_run'}
        for table in TABLES:
            if table not in existing:continue
            columns=[row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
            order=','.join('"'+c+'"' for c in columns)
            rows=[dict(r) for r in db.execute(f'SELECT * FROM "{table}" ORDER BY {order}')]
            serialized=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
            manifest['tables'][table]={'count':len(rows),'sha256':hashlib.sha256(serialized).hexdigest(),'columns':columns}
        return manifest

def compare(source_manifest,target_manifest):
    mismatches={}
    for table,info in source_manifest['tables'].items():
        other=target_manifest.get('tables',{}).get(table)
        if not other or info['count']!=other.get('count') or info['sha256']!=other.get('sha256'):
            mismatches[table]={'expected':info,'actual':other}
    return {'matched':not bool(mismatches),'mismatches':mismatches}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--compare')
    args=p.parse_args();m=build_manifest(args.source)
    if args.compare:
        with open(args.compare,encoding='utf-8') as f:other=json.load(f)
        print(json.dumps(compare(m,other),sort_keys=True))
    else:print(json.dumps(m,sort_keys=True))
