"""Create a NEW synthetic DB with an assigned ride and explicit fake observations.

Calls the shared Core with exact local fixture approvals. Never updates an
existing DB or connects a device. Restarting the app does not refresh observations.
"""
import argparse
import json
import secrets
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import Core,iso
from app.db import initialize

def create(path):
    fixture=json.loads((ROOT/'fixtures/synthetic-observations.json').read_text())
    if fixture['is_production'] is not False or fixture['live_source_connected'] is not False:raise ValueError('Synthetic fixture required')
    path=Path(path)
    if path.exists():raise ValueError('既存DBは上書きしません。新しいファイル名を指定してください。')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb'):pass
    path.chmod(0o600);initialize(path);core=Core(path)
    def command(actor,kind,data):
        draft=core.prepare(actor,kind,data);key=secrets.token_hex(16)
        return core.mutate(actor,key,key,kind,{'draft_id':draft['id'],'details':draft['details']})['current']
    ride=command('rider-a1','request',{'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1})
    key=secrets.token_hex(16)
    ride=core.mutate('driver-a1',key,key,'accept',{'ride_id':ride['id'],'version':ride['version'],'stopped':True})['current']
    command('admin-a1','observation_configure',fixture['source'])
    now=time.time();observed=iso(now)
    command('admin-a1','observation_publish',{'vehicle_id':'vehicle-a1','run_id':ride['observation']['run_id'],'source_id':fixture['source']['source_id'],'observed_at':observed,'location':fixture['location'],
        'delays':[{'id':'synthetic-demo-delay','status':'active','delay_minutes':fixture['delay_minutes'],'delay_reason':'traffic','started_at':observed,'closed_at':None,'closed_reason':None,'effective_end':iso(now+300)}]})
    return path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,default=Path('var/observation-demo.sqlite3'))
    path=create(parser.parse_args().db)
    print(f'架空の依頼・引受・車両位置・5分遅延を記録しました: {path}')
    print('位置は60秒、遅延は300秒で期限切れを表示します。実車・GPS・通知には接続していません。')
