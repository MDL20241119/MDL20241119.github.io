"""Create a NEW local synthetic DB with explicit catalog/route test settings.

No driver offer, ride, passenger consent or booking is automatically created.
Existing files are never overwritten. The regular application startup does
not load these route/timing fixtures.
"""
import argparse
import json
import secrets
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import Core
from app.db import initialize

def configure(core):
    catalog=json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())
    booking=json.loads((ROOT/'fixtures/synthetic-booking.json').read_text())
    if catalog['is_production'] or booking['is_production']:raise ValueError('Only explicit synthetic fixtures are allowed')
    commands=[('service_configure',catalog['service']),*[('stop_configure',s) for s in catalog['stops']],
              ('terms_publish',catalog['terms']),*[('route_configure',r) for r in booking['routes']]]
    for kind,data in commands:
        draft=core.prepare('admin-a1',kind,data);key=secrets.token_hex(16)
        core.mutate('admin-a1',key,key,kind,{'draft_id':draft['id'],'details':draft['details']})

def create(path):
    path=Path(path)
    if path.exists():raise ValueError('既存DBは上書きしません。新しいファイル名を指定してください。')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb'):pass
    path.chmod(0o600)
    initialize(path);configure(Core(path))
    return path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,default=Path('var/booking-demo.sqlite3'))
    args=parser.parse_args();path=create(args.db)
    print(f'架空の設定を保存しました: {path}')
    print('ドライバーが提示便を登録し、利用者が本人登録・規約同意後に候補を検索してください。実運行ではありません。')
