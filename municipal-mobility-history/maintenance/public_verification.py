#!/usr/bin/env python3
"""Public verification scope, without internal review drafts or processing logs."""
import argparse,hashlib,json
from pathlib import Path

def public_audit(value):
    if value.get('schema_version')=='public_verification_scope_v1':return value
    return {'schema_version':'public_verification_scope_v1','scope':'採択・参考原票の抽出照合と重複照合の検証範囲','sampled_records':len(value.get('sample_24',{}).get('records',[])),'checked_at':value.get('sample_24',{}).get('checked_at'),'automatic_project_merge':False,'limitations':'標本照合であり、全国全自治体の全原典再読解・全件監査を意味しない。内部の検討中記述と作業ログは公開しない。元研究記録と出典は各詳細で保持する。'}

def public_evidence(value):
    if value.get('schema_version')=='public_evidence_scope_v1':return value
    independent=value.get('independent',{})
    return {'schema_version':'public_evidence_scope_v1','scope':'数値・財源・継続撤退に関する独立抜取確認','independent_sample_records':len(independent.get('records',[])),'limitations':'全件監査ではない。確認過程の旧記述や内部判定ログは掲載せず、採用済み記述と原典箇所を各案件へ掲載する。'}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--data',type=Path,required=True);args=a.parse_args()
    for name,func in [('support-audit.json',public_audit),('verification-evidence.json',public_evidence)]:
        f=args.data/name;value=func(json.loads(f.read_text()));f.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
