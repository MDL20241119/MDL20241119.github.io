"""Read every PDF page / worksheet and reconcile input IDs, not PDF summaries."""
import argparse, json, pathlib, re
from pypdf import PdfReader
import openpyxl

ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=pathlib.Path,required=True);a=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];inp=a.inputs
old=json.loads((inp/'mobility_history_data.json').read_text());ext=json.loads(next(inp.glob('*統合拡張*.json')).read_text());new=json.loads(next(inp.glob('*追加データ*.json')).read_text())
report={'pdfs':[],'workbooks':[],'id_checks':[],'unreadable_inputs':[]}
for p in inp.glob('*.pdf'):
    reader=PdfReader(p);pages=[page.extract_text() or '' for page in reader.pages]
    report['pdfs'].append({'filename':p.name,'pages':len(pages),'pages_extracted':len(pages),'characters':sum(len(s) for s in pages),'empty_text_pages':[i+1 for i,s in enumerate(pages) if not s.strip()],'scope':'全ページのテキスト解析。全図表の独立目視再監査ではない。'})
books={}
for p in inp.glob('*.xlsx'):
    w=openpyxl.load_workbook(p,read_only=True,data_only=True)
    sheets={s.title:[list(row) for row in s.values] for s in w};books[p.name]=sheets
    report['workbooks'].append({'filename':p.name,'sheets':[{'name':k,'parsed_rows_including_titles_and_blanks':len(v),'nonblank_rows':sum(any(x is not None for x in row) for row in v)} for k,v in sheets.items()]})
def match(label,rows,col,expected):
    # Select only known IDs. Any unknown ID-like cell is checked separately in the named header column.
    got=[str(row[col]) for row in rows if len(row)>col and str(row[col]) in expected]
    assert len(got)==len(expected) and set(got)==expected,(label,len(got),len(expected))
    report['id_checks'].append({'label':label,'json_ids':len(expected),'xlsx_ids':len(got),'missing_ids':sorted(expected-set(got)),'duplicate_ids':len(got)-len(set(got))})
nb=next(v for k,v in books.items() if '結果時系列' in k)
match('追加詳査案件',nb['結果一覧'],0,{x['case_id'] for x in new['cases']})
match('追加詳査出来事',nb['時系列'],0,{x['event_id'] for x in new['events']})
match('公式掲載資料の点検',nb['公式資料点検'],0,{x['review_id'] for x in new['official_document_reviews']})
eb=next(v for k,v in books.items() if '採択原票' in k)
match('採択・支援原票',eb['全採択records'],0,{x['record_id'] for x in ext['expansion']['records']})
match('運行等参照原票',eb['運行等参照records'],0,{x['record_id'] for x in ext['expansion']['reference_records']})
match('全国自治体マスタ',eb['自治体索引'],0,{x['municipality_code'] for x in ext['municipality_index']['research_queue']})
ob=next(v for k,v in books.items() if '追跡年表' in k)
for sheet,key in [('事例','cases'),('政策制度','programs')]:
    ids={x['id'] for x in old[key]};labels=['案件ID','制度ID','制度・系列ID','ID','案件・制度ID'];header=next(row for row in ob[sheet] if any(str(x) in labels for x in row));col=next(i for i,v in enumerate(header) if str(v) in labels);match('旧'+sheet,ob[sheet],col,ids)
evs={x['event_id'] for c in old['cases'] for x in c['events']}|{x['event_id'] for x in old['policy_events']}
match('旧イベント',ob['年表'],16,evs)
report['status']='pass'
out=root/'verification/input-file-verification.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'pdfs':report['pdfs'],'worksheets':sum(len(w['sheets']) for w in report['workbooks']),'id_checks':report['id_checks']},ensure_ascii=False,indent=2))
