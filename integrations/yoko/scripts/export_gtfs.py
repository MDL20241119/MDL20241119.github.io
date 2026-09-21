"""Export an existing synthetic DB to a new local directory, never publish.

Trusted local operator CLI: filesystem access is the credential boundary.
--actor is a Core authorization target, not an Internet authentication scheme.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import Core,DomainError
from app.gtfs_validation import validate

def export(path,config,output,actor='admin-a1'):
    path=Path(path);output=Path(output)
    if not path.is_file():raise ValueError('既存の試験DBを指定してください。DBは自動作成しません。')
    if output.exists():raise FileExistsError('既存の出力先は上書きしません。新しいディレクトリを指定してください。')
    result=Core(path).gtfs.export(actor,config)
    checks=validate(result['archive'])
    if checks['errors']:raise ValueError('GTFS試験プロファイルの検査に失敗しました: '+str(checks['errors']))
    output.mkdir(parents=True,exist_ok=False)
    (output/'synthetic-gtfs.zip').write_bytes(result['archive'])
    (output/'export.json').write_text(json.dumps(result['report'],ensure_ascii=False,indent=2)+'\n')
    (output/'jp-profile-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    (output/'README.md').write_text('# 架空試験用GTFS\n\n実際には利用できません。全座標・運賃・運行条件は架空です。公開用フィードではありません。\n\nGTFS ZIP内は交通マスターの許可項目のみです。export.jsonは管理者向けのID対応・検査記録であり、フィードへ同梱しません。\n\n国内検査は限定プロファイルの検査です。Canonical Validatorの実行結果、実運行との一致、受け手での経路検索の確認は別途必要です。\n')
    return result['report']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True,type=Path)
    p.add_argument('--config',type=Path,default=ROOT/'fixtures/synthetic-gtfs.json');p.add_argument('--output',required=True,type=Path);p.add_argument('--actor',default='admin-a1')
    a=p.parse_args()
    try:
        report=export(a.db,json.loads(a.config.read_text()),a.output,a.actor)
        print(json.dumps({'status':'SYNTHETIC_EXPORTED','feed_sha256':report['feed_sha256'],'output':str(a.output)},ensure_ascii=False))
    except (DomainError,ValueError,FileExistsError) as e:
        print(json.dumps({'error':getattr(e,'code',type(e).__name__),'message':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
