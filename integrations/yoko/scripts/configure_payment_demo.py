"""Create a NEW synthetic test DB with an explicitly opted-in 820 JPY fixture.

Fixture setup only, not a production fare-setting API. No ride or payment is
created. The normal application startup never loads this fixture.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import Core,packed
from app.db import initialize

def create(path):
    fixture=json.loads((ROOT/'fixtures/synthetic-payment.json').read_text())
    if fixture['is_production'] is not False or fixture['fare']['basis']!='synthetic_test_only':
        raise ValueError('Only explicitly synthetic fixture data is supported')
    path=Path(path)
    if path.exists():raise ValueError('既存DBは上書きしません。新しいファイル名を指定してください。')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb'):pass
    path.chmod(0o600);initialize(path)
    with Core(path).db(True) as db:
        db.execute("UPDATE services SET fare_json=?,revision=revision+1 WHERE id='service-a'",(packed(fixture['fare']),))
    return path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,default=Path('var/payment-demo.sqlite3'))
    path=create(parser.parse_args().db)
    print(f'架空の820円の試験設定を保存しました: {path}')
    print('実際の請求・返金は行いません。利用者が依頼し、ドライバーが引受後、管理者が決済情報を記録してください。')
