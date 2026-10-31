"""Curated status overlay. Service closure is distinct from a completed trial.

Review this mapping against the original records when the canonical data changes.
Never infer continuation from a historical start or closure from an elapsed plan.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'data/view-data.js').read_text()
data = json.loads(text[text.index('=')+1:].strip().rstrip(';'))

GROUPS = [
    dict(id='continuing', label='継続を確認', short='継続', symbol='●', color='#61e6a8', definition='2026年の運行・提供案内、稼働記録、現在を含む運行契約等を確認。方式変更や代替運行による継続を含む。'),
    dict(id='ended', label='サービス終了', short='終了', symbol='×', color='#ff756f', definition='対象の運行・サービス自体の終了を明示する記録がある。地域のすべての交通がなくなった意味ではない。'),
    dict(id='paused', label='休止・中断', short='休止', symbol='Ⅱ', color='#ffcc66', definition='運休・休止の告知を確認。再開や別方式の実証と区別し、最終確認の状態を表示。'),
    dict(id='testing', label='実証・準備', short='実証・準備', symbol='◇', color='#64c7ff', definition='導入準備、採択、研究、実証の記録。恒常的な運行・サービス提供の確認とは分ける。'),
    dict(id='completed', label='実証・制度終了', short='実証等終了', symbol='□', color='#c5a7ff', definition='期間限定の実証や支援・採択の終了・辞退。当該地域の移動サービス全体の終了は断定しない。'),
    dict(id='unconfirmed', label='現状未確認', short='未確認', symbol='？', color='#a7b1bc', definition='過年度の実績のみ、資料再掲、案内だけ、現行運営の未照合など。継続にも終了にも推定分類しない。'),
]

# Each override is category, classified scope, explanatory note.
OVERRIDES = {}
def put(category, rows):
    for case_id, scope, reason in rows:
        assert case_id not in OVERRIDES
        OVERRIDES[case_id] = (category, scope, reason)

put('continuing', [
    ('mlit_komono','予約・交通サービス','2026年の予約ポータル案内を確認。利用増や収支改善の判定は含めない。'),
    ('meti_hitachi','ひたちBRTの営業運行','2026年3月の報告で営業継続を確認。'),
    ('meti_kashiwa','柏の葉の移動サービス','2026年1月の営業サービス開始を確認。'),
    ('meti_kosai','企業シャトルを活用した市民移動','2026年の通年運行開始と市の現行案内を確認。'),
    ('meti_kasugai','石尾台おでかけサービス','移動サービスは継続。2026年に運行管理システムの役割・体制を変更。'),
    ('meti_mitoyo','共同送迎サービス','運営主体の移管後も継続し、2026年に送迎対象を拡張。'),
    ('meti_ina','買物支援サービス','買物支援は継続。ドローン配送は2024年度末で終了。'),
    ('meti_goto','医薬品等のL3定期配送','定期配送を継続し2026年に保冷品を追加。L4は別の実証段階。'),
    ('ENV-C04','石見銀山の有償運行','有償運行を継続し、2026年10月に運行形態を再実験。国のIoT実証の終了とは分ける。'),
    ('ENV-C08','NIKKO MaaSのサービス提供','2026年10月の現行サービス掲載を確認。EVの利用成果を保証する分類ではない。'),
    ('DIG-C11','チョイソコかりんちゃんの本格運行','2026年4月の公式運用案内で本格運行を確認。増車・週末運行テストは告知として区別。'),
    ('V-C02','住民の移動サービス','自動運転車は休止中。普通車の代替運行で移動サービスは継続。'),
    ('V-C06','チョイソコとよあけの運行','2028年3月までの運行契約と現行案内を確認。'),
    ('V-C07','モバイルクリニックの診療サービス','2026年4月のサービス案内を確認。'),
    ('V-C08','若葉台・新磯の地域運行','2025年の若葉台に続き、2026年3月に新磯で本格運行を開始。'),
    ('V-C11','デジタル交通券の提供','名称変更後もデジタル交通券として継続。2026年10月の改編券案内を確認。'),
    ('V-C13','5社共同経営・交通ネットワーク改革','2026年3月の実績報告と同年度方針で制度・ネットワーク改革の継続を確認。'),
])
put('ended', [
    ('mlit_miyama','山川地区の自動運転路線','2024年3月31日に対象路線の運行を終了。地域交通体系の見直しは別に記録。'),
    ('ENV-C05','コトコト感幸バス','2021年12月28日に当該バスの運行を終了。'),
    ('V-C04','松田町のるーと足柄','2026年3月31日に当該サービスを終了。'),
])
put('paused', [
    ('mlit_iinan','赤名線の自動運転運行','2026年の計画で休止継続と車両の再活用検討を確認。'),
    ('mlit_iyo','双海地区の自動運転バス','2025年8月から当面運休との告知。再開の確認記録は未収録。'),
    ('meti_eiheiji','ZEN driveの運行','保守・保証期間の満了に伴い2026年4月から当面運休。'),
    ('V-C03','ARMAによる運行','2026年6月からARMAは休止。10月のロボタクシーは別系統の実証で、ARMA再開とは扱わない。'),
])
put('testing', [
    ('mlit_hitachiota','実装に向けた支援','2027年3月までの支援延長を確認。恒常運行の継続確認ではない。'),
    ('mlit_wakkanai','自動運転の導入準備','2026年度事業の開始段階。営業運行済みとは扱わない。'),
    ('mlit_narita','空港内の複数車種の実証','実証継続の記載。恒常的な商用サービスとは分ける。'),
    ('mlit_trucks','幹線自動運転トラックの実証','補助交付決定の記録。実装・恒常運行は未確認。'),
    ('meti_shintomei','高速L4の実装準備','2026年の報告は運営機能・事業化条件の検討。'),
    ('meti_fukushima_gi','商用電動車・エネルギー管理の研究開発','事業性の条件を検討する研究開発・実証の記録。'),
    ('ENV-C09','電池交換式EVごみ収集車の実証','2026年の資料で実証継続・未商用化を確認。'),
    ('ENV-C11','EVバス等の導入計画','導入・進捗評価の記録。地域全体の実装完了とは扱わない。'),
    ('DIG-C06','小松の次段階の事業化支援','通信実証後に2026年の先行地域へ選定。営業運行完成の確認ではない。'),
    ('DIG-C08','美郷町の通信実証','2025年度の実証後、2026年度も実証に採択。恒久運営とは分ける。'),
    ('DIG-C14','モビリティハブの実装モデル研究','実証後も支払・費用分担等を含む実装モデルを検討。'),
    ('DIG-C16','関宮地域の交通再編設計','段階実証の成果をもとに、次の実装・運営条件を設計中。'),
    ('DIG-C17','外出と福祉効果の研究','2026年の調査走行・研究の記録。恒常運行の確認とは分ける。'),
    ('DIG-C18','地域モビリティ診断の研究開発','住民協議・研究開発の段階。移動サービスの稼働確認ではない。'),
    ('DIG-C19','自動運転サービス支援道の次段階','先行実証後の地域拡張・通信検証への選定記録。'),
    ('OTHER-C06','農産物の貨客混載実験','2026年の開始告知。実施結果は未照合。'),
])
put('completed', [
    ('mlit_nishikata','2017年の短期自動運転実証','短期実証の期間終期を確認。恒常サービスの開始・終了は未確認。'),
    ('mlit_izuko','Izuko Phase3の実証','2021年に当該フェーズの実証を終了。同じサービスの後続運営は未確認。'),
    ('mlit_dento','DENTOの実証','2021年4月に実証を終了。後継サービスは未確認。'),
    ('meti_yatomi','チョイソコやとみ第3期実証','当該実証を終了。2026年の後続サービスは未確認。'),
    ('meti_tepco_v2g','V2Gの実証事業','当該実証事業の終了後に成果を報告。同方式の商用継続は不明。'),
    ('meti_osaka_air','万博での空域管理PoC','2025年の実環境PoCを2026年に結果報告。別の社会実装・研究継続は分けて確認する。'),
    ('ENV-C10','EVスクールバスの3年度実証','当該実証は2023年度で終了。拡張試算を恒常サービスとは扱わない。'),
    ('ENV-C12','脱炭素先行地域の選定','2025年に制度の選定を辞退。地域の全交通施策が終了した意味ではない。'),
    ('ENV-C13','風力水素・FCフォークリフトの実証','当該供給チェーン実証は2020年度に終了。'),
    ('ENV-C15','副生水素モビリティの実証事業','当該事業は2021年度に終了。一部用途は先に終了。'),
    ('ENV-C16','小水力水素の実証','当該実証は2020年度に終了。'),
    ('ENV-C18','回生電力とEVバス充電の実証','終了評価で技術課題と当面の事業展開困難を記載。営業サービスの廃止とは分ける。'),
    ('DIG-C01','SIP東京臨海部の研究実証','当該研究実証を完了。地域のすべての自動運転事業の終了ではない。'),
    ('DIG-C05','糠平湖トンネルの通信実証','実証を完了し、固定化の電源・費用課題を報告。'),
    ('DIG-C07','松江市の2025年度通信実証','当該通信実証を完了し、運用改善の課題を報告。移動サービス全体の終了ではない。'),
    ('DIG-C09','高知市の2025年度通信実証','当該通信実証を完了し、未実装機能等の課題を報告。'),
    ('DIG-C10','総務省の通信実証への採択','事業の採択を取下げ。福山市全体の交通・自動運転サービスの終了は意味しない。'),
])

UNKNOWN_NOTES = {
    'mlit_showa':'2018年3月は当時の終了予定。実際の終了を確認した記録ではない。',
    'mlit_kamikoani':'2025年の運営調査と過去の再開は確認。2026年の実運営は未確定。',
    'mlit_okueigenji':'2025年の運行実績は確認。2026年の運行・提供案内は本台帳で未確認。',
    'mlit_fukuyama':'2019年の事業化・運行開始は確認。現在の運営は未確認。',
    'mlit_kyushu':'2026年の高度化採択は確認。採択だけで現行サービスの稼働を判定しない。',
    'mlit_gunma':'名称・広域移行と2024年度成果は確認。2026年の現行運営は未検証。',
    'mlit_conpas':'2025年の本格運用・別地区実証の記録。2026年の現行運用はこの台帳では未確認。',
    'meti_oita':'販売・利用方式の更新記録は2025年。2026年の現行提供状況は未確認。',
    'ENV-C01':'過年度は移動サービス継続、AI配車は停止。2026年の現行運行は未確認。',
    'ENV-C06':'過年度の見直し評価を収録。2026年の運行・提供状況は未確認。',
    'ENV-C07':'2026年公表の数値は2024年度の実績。公表日を現在の稼働確認日に置き換えない。',
    'ENV-C14':'2022年度の事業化移行は確認。2026年の稼働は未確認。',
    'DIG-C12':'過年度の一部実装とマイクロEV導入中断が混在。2026年の全体現況は未確認。',
    'DIG-C13':'過年度に複数サービスの継続記録あり。2026年の各サービス現況は未確認。',
    'DIG-C15':'研究報告に2026年4月の実装記載があるが、市の現行運用との独立照合は未了。',
    'OTHER-C03':'2026年の制度案内はあるが、実際の運行・利用実績は本台帳で未確認。',
    'OTHER-C04':'2026年資料は2023年度事例の再掲。現在の稼働確認ではない。',
    'OTHER-C05':'2026年資料は2023年度事例の再掲。現在の稼働確認ではない。',
    'V-C05':'2025年評価までの本格運行・改善記録。2026年の現行運行は未確認。',
    'V-C09':'2025年評価までの本格運行記録。2026年の現行運行は未確認。',
    'V-C12':'2025年公表資料の利用実績は2023年度。2026年の現行運営は未確認。',
}

by_case = {}
known_ids = {c['id'] for c in data['cases']}
assert set(OVERRIDES) <= known_ids and set(UNKNOWN_NOTES) <= known_ids
for c in data['cases']:
    category, scope, reason = OVERRIDES.get(c['id'], ('unconfirmed', '現行の運行・提供状況', UNKNOWN_NOTES.get(c['id'], '実証・採択・過年度実績等の記録から、2026年の現行運行・提供状況を確定できていません。')))
    by_case[c['id']] = dict(category=category,scope=scope,reason=reason,
        evidence_as_of=c.get('status_as_of') or '根拠時点未確認',
        raw_status=c['status'],event_ids=[ev['event_id'] for ev in c['events']],source_ids=c['source_ids'])
result = dict(as_of=data['as_of'],basis='既存の正本と出典付き表示データを個別に確認した表示用分類。新たなリアルタイム稼働調査ではない。',
    continuation_rule='2026年の運行・提供記録、現行案内、現在を含む契約等で継続を確認。過年度実績だけの場合は現状未確認。',
    canonical_sha256=hashlib.sha256((ROOT/'data/mobility_history_data.json').read_bytes()).hexdigest(),
    groups=GROUPS,by_case=by_case)
out=ROOT/'data/case-status.js'
out.write_text('/* Curated status overlay; original records remain authoritative. */\nwindow.MOBILITY_CASE_STATUS='+json.dumps(result,ensure_ascii=False,separators=(',',':'))+';\n')
print(json.dumps({g['id']:sum(v['category']==g['id'] for v in by_case.values()) for g in GROUPS},ensure_ascii=False))
