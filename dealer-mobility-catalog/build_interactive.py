"""Build the four-page interactive edition. No client data fetch is required."""
import json, re
from pathlib import Path

P = Path(__file__).resolve().parent
doc = json.loads((P / 'content.json').read_text())
records = []
for s in doc['slides']:
    if s['kind'] == 'case':
        b = s['body']
        records.append({k:b[k] for k in ['id','head','facts','payer','flow','capture','returns','gap','action','owner','criterion','raw','proof'] } | {'note':s['note']})
menus = []
for s in doc['slides']:
    if s['kind'] == 'menu':
        menus.append({k:v for k,v in s['body'].items() if k not in ['sources','examples']} | {'head':s['head']})
extras = {s['key']:s for s in doc['slides'] if s['key'] in ['P03','P13','P14','P15','P16','P17','CLOSE']}
data = {'records':records,'menus':menus,'extras':extras,'decisions':doc['decisions']}
data_json = json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')
template = (P/'interactive-template.html').read_text()
assert template.count('__DATA__') == 1
html = template.replace('__DATA__',data_json)
(P/'index.html').write_text(html)
heads = re.findall(r'<h1[^>]*>(.*?)</h1>',template)
assert len(heads)==4 and all(30<=len(h)<=36 for h in heads)
assert len(records)==88 and len(menus)==8
assert sum(r['raw']['総事業費（千円）'] is not None for r in records)==56
assert all(r['raw']['出典URL'] for r in records)
script = html.split('<script>')[-1].split('</script>')[0]
qa=P.parent/'analysis'/'interactive-qa';qa.mkdir(exist_ok=True)
(qa/'app.js').write_text(script)
notes='''# 動く町いちばん活動カタログ

中身＝上の資料作成プロンプト／動き＝動く資料ブロック。デザイン＝Neo Swiss。

| ページ | 見出し | 構造・主操作 | 根拠パネル |
|---|---|---|---|
'''
rows=[('結論と根拠：カードを押す','活動・還元先・先行例'),('結論と根拠：棒を押す','分類別の全88記録・費用記載・出所'),('因果：有料契約者数を動かす','D25の観測値・式・未確認原価'),('不足と打ち手：合意条件を仮に切り替える','判断基準・役割の選択肢・大分の条件・測定方法')]
for i,(h,(op,panel)) in enumerate(zip(heads,rows),1):notes+=f'| {i} | {h} | {op} | {panel} |\n'
notes+='''
## 数字台帳

| 項目 | 値・式 | 時点・母集団 | 出所・前提 |
|---|---|---|---|
| 掲載記録 | 88＝29＋37＋19＋3 | 添付台帳の全記録 | 販売店29、交通空白37、共創19、人材3。独立した成功事業数ではない |
| 総事業費の記載 | 56＝37＋19 | 全88記録 | 添付台帳の同名列。期間・費用範囲は不統一 |
| 総事業費の空欄 | 32＝29＋3 | 全88記録 | 空欄は0円ではない |
| 空欄の割合 | 32÷88×100＝36.4％ | 全88記録 | 小数第1位へ四捨五入 |
| 記載と空欄の差 | 56−32＝24件 | 全88記録 | 件数の差であり、成果の差ではない |
| 活動と還元先 | 8メニュー、4区分 | 編集上の整理 | 住民・地元企業・販売店・地域。実績効果の個数ではない |
| 月額会費 | 3,000円 | D25、主に2022年3月末 | 台帳「販売店29」30行、TMF p.26 |
| 会員・供給上限 | 100人 | D25、同時点 | 100人全員の有料契約は未確認 |
| 月の会費収入 | 3,000円×入力人数 | 0〜100人の試算 | 上限時300,000円。実収入、利益、大分の予測ではない |
| 上限試算との差 | 300,000円−試算収入 | 同じ料金の仮定 | 事業者会費、助成、原価は未算入 |
| 継続判断 | 4論点−仮にそろえた論点数 | 合意前の説明用 | チェックを実際の承認・実施と扱わない |
| 確認日程 | 承認後30・90・365日 | 計画上の仮定 | 基礎確認・中間判定・通年評価の案。確定日程ではない |

全88記録の数字は、HTML内の「出所と前提」タブに時点、母集団、原表の記載、一次資料URLと併せて収録。その他の原資料の数字も各記録・大分の適用条件・測定方法で確認できる。

## 操作

カード・棒を押すと根拠を表示。→／Spaceで次、←で前、1〜4でページ移動、Oで一覧、Dで自動デモ、Escでパネルを閉じる・一覧に戻る。会費の試算はスライダー、着手条件はスイッチで操作する。上部の拡大ボタンで原寸表示。

URL末尾の #static と「動きを減らす」では完成状態を表示。着手条件は仮にすべてそろえた状態になる。OSの動きを減らす設定にも対応する。

## 確認範囲

全件の現況・契約・実原価は未確認。活動と還元は大分への提案・仮説。合意・実施・効果測定は未実行。金額の不明値はxx。

旧106枚は catalog.html に保存。今回の4ページは会議の入口であり、全88記録を根拠パネルに同梱している。40KBの目安より大きいのは、このデータを単一HTMLに保持するため。
'''
(P/'interactive-notes.md').write_text(notes)
print(json.dumps({'pages':4,'records':len(records),'heads':[len(h) for h in heads],'bytes':len(html.encode()),'data_bytes':len(data_json.encode())},ensure_ascii=False))
