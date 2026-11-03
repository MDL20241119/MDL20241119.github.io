from pathlib import Path
import json,runpy,html
P=Path(__file__).resolve().parent;R=P.parent.parent
H=runpy.run_path(str(P/'build_page.py'));globals().update({k:H[k] for k in ['chapter','detail','table','link','photo','fmt']})
D=json.loads((P/'downloads/Beppu-Tourism-Data.json').read_text());Y=json.loads((P.parent/'yufuin-mobility/downloads/Yufuin-Field-Evidence.json').read_text())
items=[
('観光客総数・日帰り・宿泊','市公表値','2019〜2025年、2025四半期。月別は宿泊のみ。','#visitors'),
('国内・外国、外国人国/地域','市公表推計','2024/2025改訂版、2025外国人22区分。旧推計との長期比較不可。','#stay'),
('国内の発地','市宿泊の地域構成','外国を含む全宿泊の構成。全来訪者の国内発地ではない。','#stay-detail'),
('訪問理由・未訪問理由・同行者','市単独未確認','県の訪問理由と改善希望は掲載。別府回答だけの集計には代用しない。','#stay-detail'),
('月別季節性','宿泊/施設入込を区別','2024/2025市宿泊、2025外国人宿泊、19施設入込。','#visitors'),
('地区別に泊まる場所','市公表値','北浜中央/鉄輪明礬/堀田観海寺/その他の2024/2025。','#stay'),
('市の観光消費総額・単価','県単価×市人数','2025年4区分、改訂後2024比較。市直接支出調査ではない。','#stay'),
('訪日客の費目別消費','市単独未確認・県参考','観光庁公式県別2025費目。別府の支出/移動費に読み換えない。','#stay-detail'),
('訪日客の直近4四半期支出','市単独未確認','湯布院の民間個票再集計に相当する別府市値は今回未確認。','#coverage'),
('平均泊数・宿泊日数','別定義を併記','市KPI1.106泊/2025回答施設1.103泊/県質問紙泊数。','#stay-detail'),
('客室稼働率・施設数','国の市別回答施設','2025従業者10人以上と2026客室20室以上を分離。','#stay-detail'),
('時間単位の市内滞在','市全体未確認','宿泊日数、定期観光3時間、駐車容量では代用しない。','#coverage'),
('観光客の交通手段','市単独未確認','県4,942人・海外居住200人の複数回答を別枠表示。','#mobility'),
('住民の交通手段・困りごと','市/中部圏を区別','2021市民853人。2026計画中部圏1,142人は別府単独ではない。','#mobility'),
('観光バス台数・乗客数','市全体未確認','県貸切バス事業実績・調査回答・定員・駐車容量を分離。','#mobility'),
('観光/高速バス便・運賃','事業者の現行案内','定期地獄めぐり、秋限定オープントップ、フリー券、運休。','#mobility'),
('鉄道・空港・港のアクセス','公式案内と年度実績','JR3駅、2024港/空港、空港バス、船の公式時刻。','#mobility'),
('GWの交通・観光','2026期間限定速報','8日間の高速乗降車/船舶降客降車/13施設/34宿泊施設。','#mobility'),
('駅の荷物保管・宿配送','提供者案内','ヤマト/WANDER COMPASS/特定3ホテル。空港配送は中止中。','#mobility'),
('宿の送迎・最終到着便接続','市横断値未確認','対象宿の車両・時間別稼働・利用件数・費用は未確認。','#coverage'),
('地域間回遊・訪問順序','圏域人流/市単独未確認','2024年10月中部圏人流。別府翌日最初の立寄り先は未確認。','#mobility'),
('地点別乗降OD','GLOBAL標本あり','聞き取り2,171件の起終点区分。全実車5,187件と別母数。','#mobility'),
('コミュニティ交通実証','計画・議事・現行条件','延長期間/南部循環線。全サービス年間収支の一覧は未確認。','#plans'),
('タクシー車両・人員・実績','国の営業区域集計','2024年度別府市営業区域。稼働率を現在の空車率にしない。','#mobility'),
('公共交通費・委託費・収支','計画KPI/一部未確認','市行政負担KPI、県財政負担目標。全実証の確定費用一覧は未確認。','#plans'),
('渋滞・待ち時間・駐車','地点/時期限定','駅前本町の解除候補、寄港時待ち列、大型駐車6台。通年待ち時間未確認。','#mobility'),
('夜の外出・移動断念・消費効果','市単独未確認','県夜間観光改善希望は意見。帰りの不成立人数や因果効果ではない。','#coverage'),
('国・県・市の交通計画','現行原典確認','第3次国計画、県2026ビジョン、市2027/9終期、九州広域計画。','#plans'),
('国・県・市の観光計画','現行原典確認','国2026〜2030、県2025〜2027、市2025〜2029。市DX計画2030も併記。','#plans')]
M={
'訪問を見送った理由':('別府市単独の同等調査は未確認。県の不満・希望は、未訪問理由ではない。','#stay-detail'),
'現地の声':('市2021住民アンケート、県中部圏アンケート、2026協議会議事。来訪者と住民を分ける。','#mobility'),
'団体の調査漏れ':('別府単独の団体抽出・未回答率は未確認。県の観光バス複数回答を団体比率にしない。','#coverage'),
'日帰り・宿泊':('市2025入込統計と外国人改訂推計あり。駅周辺の同じ400人調査ではない。','#visitors'),
'誰が時間を決めるか':('別府について旅行会社が決める滞在枠・実滞在の聞取り公表値は未確認。','#coverage'),
'旅行の組み合わせ':('中部圏携帯人流はあるが、別府と福岡の旅行者別宿泊組合せは未確認。','#mobility'),
'貸切行程':('地獄めぐり約3時間、秋別府〜由布院約65分の予定仕様。平均実滞在ではない。','#mobility'),
'地域間回遊':('2024年10月中部圏ODあり。別府観光客の同日周遊先・順序の同等表は未確認。','#mobility'),
'既存の受け皿':('鉄輪地獄地帯公園小倉地区・大型6台を確認。稼働率は未確認。','#mobility'),
'ツアー実績の取り寄せ':('別府で同一要件のツアー助成実績・参加者数は今回未確認。','#coverage'),
'消費の測り方':('市は県単価×人数。県公式費目を別枠掲載。ツアー別買物実額は未確認。','#stay'),
'訪日客の市内支出':('別府市内の訪日客費目別単価は未確認。県公式単価を別府値にはしない。','#stay-detail'),
'住民への影響':('市民モード/中部圏調査、寄港時列を確認。新交通による住民負担の因果測定は未確認。','#mobility'),
'住民の交通供給':('市計画/実証延長/南部循環仕様あり。最新全実証の年間輸送・委託費は未確認。','#plans'),
'既存観光便':('別府地獄めぐり・オープントップの仕様。実利用/便・収支は未確認。','#mobility'),
'荷物と乗継':('駅の預かり・配送と特定宿サービス。地域全体の車両/対象宿数・実績は未確認。','#mobility'),
'支出と泊数':('国2025県訪日費目と別府市回答施設の延べ/実人数を確認。市訪日個票同等集計は未確認。','#stay-detail'),
'交通供給':('2024年度別府営業区域351両、実働44.91%、輸送1,372,853人。','#mobility'),
'住民の移動':('南部循環・生活路線を分離。最新スクールバス/コミュニティ年間人数の同等表は未確認。','#plans'),
'宿泊と周遊':('別府宿泊後の翌日最初の立寄り先の同等公開表は未確認。','#coverage'),
'宿泊施設の供給':('国の2025/2026市別参考表で回収数・稼働率・延べ/実人数を確認。','#stay-detail'),
'無料デマンド実験':('湯布院の2020無料実験に同条件で対応する別府実験は未確認。GLOBALは別制度・別標本。','#mobility')}
body='<p class="intro">湯布院ページの項目を棚卸しし、別府で確認できる値、県・圏域の参考値、今回確認できなかった値を整理しました。「未確認」は存在しないという意味ではありません。異なる地域の数字で空欄を埋めず、次に必要な観測を残します。</p>'
body+=detail('主要29項目の対応と確認範囲',table('湯布院と同じ問いで、別府の資料を確認する',['分析項目','確認状態','使える範囲・不足'],[[a,b,c+' '+f'<a href="{url}">本文へ ↓</a>'] for a,b,c,url in items],True))
rows=[];records=[]
for r in Y['records']:
 result,url=M[r['topic']];rows.append([r['id']+' / '+r['topic'],r['indicator'],result+f' <a href="{url}">関連箇所 ↓</a>']);records.append({'yufuin_record':r['id'],'topic':r['topic'],'indicator':r['indicator'],'beppu_status':result,'page_anchor':url})
body+=detail('湯布院の補足56項目を、1件ずつ確認する',table('地域固有の実験を、そのまま別府の実績として置き換えない',['湯布院側のID/分野','元の調査項目','別府側の対応と限界'],rows,True))
body+='<h3 style="margin-top:40px">足りないデータを、次の計測へ</h3><div class="triple"><article class="panel"><h3>いつ、どこで困るか</h3><p class="micro">平日・休日・寄港日別に、待ち時間、配車不成立、最終便後、荷物や介助の有無を揃えて観測。年間客数から必要台数を決めない。</p></article><article class="panel"><h3>既存の足で成立するか</h3><p class="micro">既存バス・タクシー・宿送迎・荷物配送で帰宿が成立する割合と調整時間を先に確認。新車ありきにせず、情報改善や共同手配とも比べる。</p></article><article class="panel"><h3>地域に何が残るか</h3><p class="micro">街への立寄り・滞在・支出の変化を、天候・イベント・客層の近い比較対象と照合。個人の行動履歴を公開せず、匿名集計で検証する。</p></article></div>'
body+='<h3 style="margin-top:40px">原典とデータを確認する</h3><p class="micro">数字の意味を戻って確かめられるよう、元資料へのリンクを本文にも併記しています。Excel・PDFの掲載値と計算値を区別し、丸め、母集団変更、不一致を注記しています。</p><div class="download-row">'
for fn,title in [('Beppu-Tourism-Data.json','観光・宿泊・消費データ JSON'),('Beppu-Monthly-Lodging-2025.csv','月別宿泊データ CSV'),('Beppu-Transport-Evidence.json','交通実績・ODデータ JSON'),('Beppu-Policy-Data.json','現行計画・目標データ JSON'),('Beppu-Coverage.json','29分野・56項目対応 JSON')]:body+=f'<a class="button-link" download href="downloads/{fn}">{title} ↧</a>'
body+='</div><ol class="source-list">'
sources=[('別府市2025年観光動態要覧','https://www.city.beppu.oita.jp/doc/sangyou/kankou/toukei_r07toukei.pdf','方法1〜2頁、結果4〜10頁。2026年10月発行。外国人推計は改訂後。'),('別府市観光統計・公式Excel','https://www.city.beppu.oita.jp/doc/sangyou/kankou/toukei_r07toukei.xlsx','表3宿泊/外国人/地区、表4主要施設。月別観光客総数ではない。'),('観光庁・宿泊旅行統計調査','https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html','月別原表への直接リンクは02+章。2026区分変更に注意。'),('観光庁・2025都道府県別訪日消費','https://www.mlit.go.jp/kankocho/content/002020056.xlsx','大分県全体。別府市の値ではない。'),('大分県2025年度観光実態調査','https://www.pref.oita.jp/uploaded/attachment/2268519.pdf','20地点、4,942人。県全体複数回答と費目別分母の限界。'),('別府市統計書・第10章交通','https://www.city.beppu.oita.jp/doc/sisei/toukei_housei/toukei/toukeisho/r07/10.pdf','2026年3月公表。各社輸送集計を市内観光実人数にしない。'),('九州運輸局2024年度タクシー営業区域集計','https://wwwtb.mlit.go.jp/kyushu/content/000363303.pdf','別府市営業区域、印刷8頁/PDF12頁。'),('GLOBAL・国交省審議会提出資料','https://www.mlit.go.jp/policy/shingikai/content/001912856.pdf','2025/9/29連絡協議会提出。聞き取り速報、期間・標本を区別。'),('大分県交通ビジョン2026・資料編','https://www.pref.oita.jp/uploaded/attachment/2276664.pdf','人流、県民調査、路線輸送、事業者意見。中部圏と別府を分離。'),('別府市地域公共交通計画','https://www.city.beppu.oita.jp/doc/seikatu/bouhan_anzen/koukyou_koutuu/koukyou_kassei/plan.pdf','掲載本文の期間は2027年9月まで。計画基準年を現在としない。')]
for title,url,note in sources:body+=f'<li><a href="{url}">{title} ↗</a><small>{note}</small></li>'
body+='</ol>'+photo('bay','田ノ浦ビーチから望む別府湾と別府市街','別府湾と別府市 / Project Kei / 2021年 / CC BY-SA 4.0')
(P/'coverage-section.html').write_text(chapter(5,'coverage','COVERAGE, LIMITATIONS & SOURCES','同じ問いで比べる。<br>違う数字を、混ぜない。',body))
(P/'downloads/Beppu-Coverage.json').write_text(json.dumps({'as_of':'2026-11-04','scope':'Beppu research coverage, not equivalence of measurements','main_topics':[dict(zip(['topic','status','scope','anchor'],r))for r in items],'field_records':records},ensure_ascii=False,indent=2))
# Add newly verified transport evidence without changing the original proposal.
p=P/'mobility-section.html';s=p.read_text();marker='<h3 style="margin-top:45px">GLOBALは、どこからどこへ使われたか</h3>'
extra='<h3 style="margin-top:45px">タクシーは「車両数」だけでは測れない</h3><div class="metric-grid"><div class="metric"><p class="label">2024年度・別府市営業区域</p><p class="big-number">351<small>両</small></p><p class="micro">期末車両数。運転者は期末290人。</p></div><div class="metric"><p class="label">年間輸送人員</p><p class="big-number">137.3<small>万人</small></p><p class="micro">1,372,853人 / 輸送回数880,375回。</p></div><div class="metric"><p class="label">延実働車両 / 延実在車両</p><p class="big-number">44.91<small>%</small></p><p class="micro">年間の実働率。今の空車率・時間帯の配車可能率ではない。</p></div></div>'
extra+=detail('国のタクシー・県貸切バス原表を確認',table('2024年度・別府市営業区域、九州運輸局公表',['指標','一般','一人一車','合計'],[['車両数（期末・両）',321,30,351],['運転者（期末・人）',260,30,290],['年間輸送回数',827881,52494,880375],['年間輸送人員',1289077,83776,1372853],['営業収入（千円）',1062061,80147,1142208],['実働率（%）',42.19,74.26,44.91]],True)+'<p class="micro">2024/4〜2025/3、2025/7/31まで提出分。福祉輸送限定・実績のない休止事業者等は除外。営業収入は利益ではありません。</p>'+link('https://wwwtb.mlit.go.jp/kyushu/content/000363303.pdf#page=12','九州運輸局2024年度・印刷8頁')+table('大分県の貸切バス事業実績。別府到着バス数ではない',['年度','期末車両 両','年度輸送 千人'],[[2018,327,1400],[2019,302,1157],[2020,302,445],[2021,278,518],[2022,276,724],[2023,262,910],[2024,270,1015]])+'<p class="micro">県内事業者のストックとフロー。観光以外を含み得て、県外車両の別府来訪を網羅しません。</p>'+link('https://wwwtb.mlit.go.jp/kyushu/toukei/j_koutuu/file02.htm','九州運輸局・貸切バス事業概況'))
extra+='<div class="note"><strong>中部圏の生活交通の声。</strong>2026公表県計画収録のWeb調査は中部圏1,142人。乗継ぎの不便・不安46%、待合環境37%、行先・時刻の調べ方32%。別府単独ではなく、調査時期は方法欄で未確認。高齢層が少ない標本です。'+link('https://www.pref.oita.jp/uploaded/attachment/2276664.pdf','県資料編32／103〜104頁')+'</div>'
if 'タクシーは「車両数」だけでは測れない' not in s:s=s.replace(marker,extra+marker)
s=s.replace('</section>','<div class="note"><strong>南部循環線は、日中の定時定路線。</strong>2026年10月公式チラシは平日10便、始発8:30・最終13:40、1回300円、現金のみ。電動リフト車で6人＋車椅子1台。実証は2027/4/30まで。夜間のGLOBALとは別サービスです。'+link('https://www.city.beppu.oita.jp/seikatu/bouhan_anzen/koukyou_koutuu/rideshare.html','別府市の南部循環線案内')+'</div></section>') if '南部循環線は、日中の定時定路線。' not in s else s
p.write_text(s)
# Origin shares retain the original all-lodging denominator.
p=P/'stay-detail.html';s=p.read_text();origin=D['city_overnight_origin_2025'];orig=detail('宿泊客はどの地域から来るか',table('2025年別府市・全宿泊推計の地域構成（外国を含む）',['発地','割合 %'],[[x['origin'],x['pct']] for x in origin['data']])+'<p class="micro">国内客だけを分母とした発地割合ではありません。全観光客の発地とも異なります。丸めの合計は99.9%。</p>'+link(origin['source_url']+'#page=7','市観光動態要覧・4頁'))
if '宿泊客はどの地域から来るか' not in s:s=s.replace('<h3 style="margin-top:35px">2025年・月別客室稼働率</h3>',orig+'<h3 style="margin-top:35px">2025年・月別客室稼働率</h3>')
p.write_text(s)
print('Coverage, taxi and origin evidence built')
