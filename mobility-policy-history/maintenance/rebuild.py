from pathlib import Path
import json, shutil, re, hashlib, collections, base64
from openpyxl import load_workbook
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT
(ROOT/'verification').mkdir(exist_ok=True)
RAW=ROOT/'data/mobility_history_data.json'
D=json.loads(RAW.read_text())
SM={s['source_id']:s for s in D['sources']}
PM={p['id']:p for p in D['programs']}
CM={c['id']:c for c in D['cases']}
ALL_EVENTS=[e for c in D['cases'] for e in c['events']]+D['policy_events']
COUNTS={'cases':len(CM),'programs':len(PM),'case_events':sum(len(c['events']) for c in D['cases']),'policy_events':len(D['policy_events']),'events':len(ALL_EVENTS),'sources':len(SM),'detailed_cases':len(D['detailed_case_ids'])}
assert all(COUNTS[k]==D['counts'][k] for k in ['cases','programs','case_events','policy_events','sources','detailed_cases']),COUNTS
assert len({e['event_id'] for e in ALL_EVENTS})==COUNTS['events']
assert set(D['detailed_case_ids'])<=set(CM)
unresolved=[]
for obj in [*D['cases'],*D['programs'],*ALL_EVENTS,*D['claims']]:
    for sid in obj.get('source_ids',[]):
        if sid not in SM: unresolved.append([obj.get('id',obj.get('event_id')),sid])
assert not unresolved,unresolved
assert all(p in PM for c in D['cases'] for p in c['program_ids'])

# Reconcile every ID and the published URL of each source with the Excel ledger.
W=load_workbook(ROOT/'downloads/mobility-history-ledger.xlsx',read_only=True,data_only=True)
ledger={s.title:[list(r) for r in s.values][7:] for s in W}
assert {r[0] for r in ledger['事例']}==set(CM)
assert {r[0] for r in ledger['政策制度']}==set(PM)
assert {r[16] for r in ledger['年表']}=={e['event_id'] for e in ALL_EVENTS}
assert {r[1] for r in ledger['出典']}==set(SM)
assert all(r[3]==SM[r[1]]['url'] for r in ledger['出典'])

ORIGINS={'mlit':'国土交通省','meti':'経済産業省','environment':'環境省','digital':'デジタル庁・内閣府・総務省等','other':'その他府省・横断','claims_verification':'地域独自・横断検証'}
AGENCY_ORDER=['国土交通省','経済産業省','環境省','デジタル庁','内閣府','内閣官房','総務省','農林水産省','厚生労働省','警察庁','関係府省・地域独自']
def as_text(v):
    if v is None:return ''
    if isinstance(v,str):return v
    if isinstance(v,list):return ' / '.join(map(as_text,v))
    if isinstance(v,dict):return ' / '.join(str(k)+': '+as_text(x) for k,x in v.items())
    return str(v)
def agencies(o,case=False):
    raw=as_text(o.get('lead') or o.get('agency'))
    if not raw and o.get('origin') in ('mlit','meti','environment','other'):
        raw=ORIGINS[o['origin']]
    if case:
        raw+=' '+as_text(o.get('actors'))
        for pid in o.get('program_ids',[]):raw+=' '+as_text(PM[pid].get('lead') or PM[pid].get('agency') or ORIGINS[PM[pid]['origin']])
        if o.get('origin')=='claims_verification':raw+=' 関係府省・地域独自'
    if '国交' in raw:raw+=' 国土交通省'
    if '経産' in raw:raw+=' 経済産業省'
    if '農水' in raw:raw+=' 農林水産省'
    return [a for a in AGENCY_ORDER[:-1] if a in raw] or ['関係府省・地域独自']
THEMES={
 '自動運転':r'自動運転|自動走行|自律移動|ラストマイル|隊列|L[234]運転支援',
 'MaaS':r'MaaS|BaaS|マース|モビリティハブ|モビリティ・ハブ',
 'オンデマンド':r'デマンド|オンデマンド|チョイソコ|のるーと|のるイコ|予約配車',
 '交通空白':r'交通空白|交通弱者|移動困難|買物困難|移動支援|生活交通|中山間',
 '共同運行':r'共同運行|共同経営|共同送迎|ゴイッショ|車両共同|共同利用|企業シャトル|輸送資源',
 '物流・貨客混載':r'物流|配送|貨客|貨物|ドローン|宅配|ロッカー|トラック|フォークリフト',
 'EV・脱炭素':r'脱炭素|低炭素|CO2|EV|V2G|V2H|電動|水素|再エネ|FCV|FCバス|グリーンスロー',
 'データ・通信':r'データ|通信|5G|DX|ITS|標準|COMmmmONS|サイバー|デジタル',
 '医療・福祉':r'医療|福祉|介護|診療|フレイル|病院|健康|通院|通所',
 '観光':r'観光|旅行|回遊|周遊|リゾート|感幸'
}
def theme_tags(o):
    # Browsing labels only. A text match never creates a subsidy/causal relationship.
    text=as_text({k:o.get(k) for k in ['name','intervention','purpose','trajectory','actors','outputs','public_value_observation']})
    tags=[k for k,pat in THEMES.items() if re.search(pat,text,re.I)]
    return tags or ['その他']
def state_tags(c):
    s=as_text(c.get('status'))
    out=[]
    if re.search('休止|運休|停止|中断',s):out.append('休止・中断を記録')
    if re.search('終了|辞退|取下げ|困難',s):out.append('終了・辞退等を記録')
    positive=re.sub(r'(?:継続|実装|運行|本格運行|稼働|最新運営実績)[は・、 ]*(?:個別)?(?:未検証|未確認|未確定)','',s)
    if re.search('継続|本格|実装|通年|稼働|運用実績|路線運行',positive):out.append('運行・実装等を記録')
    if re.search('移行|変更|見直し|修正|再設計|代替|転換|再編|移管',s):out.append('変更・代替を記録')
    if re.search('実証|研究|計画|採択|導入支援|検討|開始段階|構築',s):out.append('実証・研究・採択等')
    if re.search('未確認|未検証|未確定|限定|紹介|報告あり',s):out.append('不足・未確認あり')
    return out or ['不足・未確認あり']

def strip_evidence(o):
    return {k:v for k,v in o.items() if k not in ['evidence_records','timeline','sources']}

V={k:D[k] for k in ['schema_version','report_title','as_of','coverage','id_mapping','detailed_case_ids','interpretation_rules','evidence_freeze','public_information_only','gaps']}
V['counts']=COUNTS
V['source_case_event_records']=sum(max(1,len(e.get('source_observations',[]))) for c in D['cases'] for e in c['events'])
V['agencies']=AGENCY_ORDER
V['themes']=list(THEMES)+['その他']
V['states']=['運行・実装等を記録','変更・代替を記録','休止・中断を記録','終了・辞退等を記録','実証・研究・採択等','不足・未確認あり']
V['programs']=[]
for p in D['programs']:
    o=strip_evidence(p);o['agencies']=agencies(p);o['themes']=theme_tags(p)
    o['aliases']=list(dict.fromkeys([*p.get('original_ids',[]),*[r.get('name','') for r in p.get('evidence_records',[])]]))
    V['programs'].append(o)
V['cases']=[]
for c in D['cases']:
    o=strip_evidence(c);o['agencies']=agencies(c,True);o['themes']=theme_tags(c);o['states']=state_tags(c)
    o['prefectures']=re.findall(r'北海道|東京都|大阪府|京都府|[一-龥]{2,3}県',c.get('region','')) or ['広域・全国等']
    o['aliases']=list(dict.fromkeys([*c.get('aliases',[]),*c['original_ids'],*[r.get('name','') for r in c['evidence_records']]]))
    V['cases'].append(o)
V['policy_events']=D['policy_events'];V['sources']=D['sources']
V['claims']=[c for c in D['claims'] if c['id'] in ['mlit_claim_1','M06','V21']]
if (ROOT/'verification/external-link-check.json').exists():
    checks=json.loads((ROOT/'verification/external-link-check.json').read_text())
    by_id={r['source_id']:r for r in checks['results']}
    for s in V['sources']:
        r=by_id.get(s['source_id'])
        if r:s['link_check']={'status':r['status'],'checked_at':'2026-10-31','method':'HTTP GET（先頭部分のみ）'}
    V['link_check_summary']=checks['summary']

# Map the report's 25 detailed case sections, retaining page boundaries.
R=PdfReader(ROOT/'downloads/mobility-history-report.pdf')
section_pages={}
for i in range(14,41):
    t=R.pages[i].extract_text() or ''
    match=next((id for id in D['detailed_case_ids'] if re.search(r'｜\s*'+re.escape(id)+r'\s*\n',t)),None)
    if match:section_pages[match]=[i+1]
    elif section_pages:section_pages[next(reversed(section_pages))].append(i+1)
assert len(section_pages)==D['counts']['detailed_cases'],section_pages
V['detail_pages']=section_pages

OUT.mkdir(parents=True,exist_ok=True)
(OUT/'data').mkdir(exist_ok=True);(OUT/'downloads').mkdir(exist_ok=True)
# The canonical JSON stays in place.
# The research PDF stays in place.
# The reconciliation workbook stays in place.
(OUT/'data/view-data.js').write_text('window.MOBILITY_DATA='+json.dumps(V,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n')

audit={
 'as_of':D['as_of'],'canonical_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'counts':COUNTS,
 'excel_rows':{k:len(v) for k,v in ledger.items()},'excel_id_sets_match':True,'excel_source_urls_match':True,
 'event_ids_unique':True,'source_references_resolve':True,'case_program_references_resolve':True,
 'precision_distribution':dict(collections.Counter(e['date_precision'] for e in ALL_EVENTS)),
 'original_case_event_records':D['counts']['source_case_event_records'],
 'merged_event_groups':sum(bool(e.get('source_observations')) for e in ALL_EVENTS),
 'undated_event_ids':[e['event_id'] for e in ALL_EVENTS if e['date_precision']=='unknown'],
 'pdf_pages':len(R.pages),'detailed_case_page_map':section_pages,
 'input_files_are_local_canonical_copies':True,
 'method':'State/theme labels are search aids; original status text, attribution text, dates, observations and raw canonical JSON are preserved.'
}
(ROOT/'verification/data-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
(ROOT/'verification/view-data.json').write_text(json.dumps(V,ensure_ascii=False))
print(json.dumps({'counts':COUNTS,'excel':'all IDs and source URLs match','source_references':'all resolve','detail_sections':len(section_pages),'view_data_bytes':(OUT/'data/view-data.js').stat().st_size},ensure_ascii=False))
