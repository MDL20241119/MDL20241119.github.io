#!/usr/bin/env python3
"""Synchronize the four founding documents from founding.json.

Run from any directory. HTML is the canonical copy consumed by build_pdf.py.
No account data, credentials, or private contact details belong in this source.
"""
from pathlib import Path
from html import escape
import json
import re
import argparse

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
BASE = '/oita-mirai-mobility-consortium/'
DATA = json.loads((ROOT / 'documents/founding.json').read_text())
VERSION = DATA['version']
TARGET = DATA['target_date_label']
DOCS = DATA['documents']


def node(markup):
    return html.fragment_fromstring(markup)


def markup(el):
    return html.tostring(el, encoding='unicode', method='html')


def save(path, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<!DOCTYPE html>\n' + markup(root) + '\n')


def doclink(key, fragment=''):
    doc = next(x for x in DOCS if x['key'] == key)
    return BASE + doc['path'] + (('#' + fragment) if fragment else '')


def docnav(active):
    links = ''.join(f'<a href="{doclink(d["key"])}"' +
                    (' aria-current="page"' if d['key'] == active else '') +
                    f'><b>{d["number"]}</b><span>{escape(d["label"])}</span></a>' for d in DOCS)
    return f'<nav aria-label="設立文書4点" class="founding-doc-nav">{links}</nav>'


def related(keys):
    return '<div class="document-links"><h3>関連する文書</h3><ul>' + ''.join(
        f'<li><a href="{doclink(k)}">{escape(next(x["title"] for x in DOCS if x["key"] == k))} →</a></li>'
        for k in keys) + '</ul></div>'


def table(headers, rows, widths=None):
    attrs = f' data-pdf-widths="{widths}"' if widths else ''
    return f'<table{attrs}><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in headers) + \
        '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(
            f'<th scope="row">{v}</th>' if i == 0 else f'<td data-label="{headers[i]}">{v}</td>'
            for i, v in enumerate(row)) + '</tr>' for row in rows) + '</tbody></table>'


def proposal(title, text):
    return f'<div class="proposal-block"><span class="unsettled-tag">未決・提案</span><h3>{title}</h3>{text}</div>'


def article(number, title, text):
    return f'<div class="rule-article"><h3>第{number}条｜{title}</h3>{text}</div>'


def founder_summary():
    items = ''.join(f'<li><strong>{escape(x["name"])}</strong><span>' +
                    ('募集中' if x['name'] == '県内各自治体' else '参画を協議') + '</span></li>'
                    for x in DATA['founder_groups'])
    return '<div class="founder-summary" id="founder-groups"><h3>発起人は、この5区分。</h3>' + \
        f'<ul class="founder-groups">{items}</ul><p class="note">発起人構成の提案です。県内各自治体は募集中。自治体の個別名は、参画と掲載の了承を確認してから掲載します。</p><a href="{doclink("members")}">発起人・会員・役員名簿を見る →</a></div>'


def pvmv():
    items = ''.join(f'<div class="pvmv-item"><h3>{label}</h3><p class="pvmv-statement">{escape(DATA[key])}</p></div>'
                    for key, label in [('purpose', 'Purpose'), ('vision', 'Vision'), ('mission', 'Mission')])
    values = ''.join(f'<li>{escape(x)}</li>' for x in DATA['values'])
    return '<div class="pvmv-block" id="pvmv"><h3>私たちが目指すこと。</h3>' + items + \
        f'<div class="pvmv-item"><h3>Values</h3><ul class="pvmv-values">{values}</ul></div></div>'


def add_common_style(root):
    # Remove text left outside style elements by the earlier fragment parser.
    stray_font = re.compile(r"@font-face\{font-family:Oita;src:url\('[^']*proposal-jp-(?:regular|black)\.woff[^']*'\)[^}]*\}")
    body = root.find('body')
    if body is not None:
        body.text = stray_font.sub('', body.text or '') or None
        for element in body.iterdescendants():
            element.tail = stray_font.sub('', element.tail or '') or None
    for link in root.xpath('//link[contains(@href,"founding-documents.css")]'):
        link.getparent().remove(link)
    root.find('head').append(node(f'<link rel="stylesheet" href="{BASE}assets/founding-documents.css?v={VERSION}">'))
    for style in root.xpath('//style[@data-founding-fonts]'):
        style.getparent().remove(style)
    fonts = f"@font-face{{font-family:Oita;src:url('{BASE}read/main/assets/proposal-jp-regular.woff?v={VERSION}') format('woff');font-weight:400 600;font-display:swap}}@font-face{{font-family:Oita;src:url('{BASE}read/main/assets/proposal-jp-black.woff?v={VERSION}') format('woff');font-weight:700 900;font-display:swap}}"
    fontstyle = node('<style data-founding-fonts="1"></style>')
    fontstyle.text = fonts
    root.find('head').append(fontstyle)
    # The latest Oita subsets cover the complete four-document copy.
    for style in root.xpath('//style'):
        style.text = re.sub(r"url\('(?:/oita-mirai-mobility-consortium/read/main/|\.\./read/main/)?assets/proposal-jp-(regular|black)\.woff(?:\?[^']*)?'\)",
                            lambda m: f"url('{BASE}read/main/assets/proposal-jp-{m[1]}.woff?v={VERSION}')", style.text or '')


def sync_main():
    path = ROOT / 'read/main/index.html'
    root = html.fromstring(path.read_text())
    root.find('head/title').text = '構想説明書・設立趣意書｜大分未来モビリティ'
    root.xpath('//div[@class="book-top"]/h1')[0].text = '構想説明書・設立趣意書'
    for old in root.xpath('//div[@class="book-top"]/p[@data-founding-target]'):
        old.getparent().remove(old)
    root.xpath('//div[@class="book-top"]/h1')[0].addnext(node(f'<p class="publication-update" data-founding-target="1"><strong>設立目標：{TARGET}</strong></p>'))
    for old in root.xpath('//*[@id="pvmv" or @id="founder-groups"]'):
        old.getparent().remove(old)
    purpose_body = root.xpath('//*[@id="main_ch01"]/div[@class="chapter-body"]')[0]
    purpose_body.insert(0, node(pvmv()))
    note = purpose_body.xpath('.//p[@class="note"]')[-1]
    note.clear()
    note.set('class', 'note')
    note.text = 'まずは任意団体として立ち上げます。コンソーシアムは共同案件をつくり、おおいたプラットを含む各事業者の実行につなぐ枠組みです。発起人としての役割と、個別事業で担う役割は分けて相談します。'
    founders_body = root.xpath('//*[@id="main_ch03"]/div[@class="chapter-body"]')[0]
    founders_body.insert(0, node(founder_summary()))
    for s in root.xpath('//*[@id="main_ch03"]//span[@class="eyebrow"]'):
        if s.text in ('共同代表候補', '事務局長候補'):
            for tag in list(s):
                if tag.get('class') == 'approval-tag':
                    s.remove(tag)
            s.append(node('<span class="approval-tag">了承待ち</span>'))
    for strong in root.xpath('//div[@class="milestones"]/div/strong'):
        if strong.text_content().strip() in ('2027.1', '2027.1.26'):
            strong.clear(); strong.text = '2027.1.26'
    chapter2 = root.get_element_by_id('main_ch02')
    lead = chapter2.xpath('.//header/p')[0]
    lead.text = f'構想はJMSで発表済み。{TARGET}の設立を目標に、人材育成と設立準備を並行して進めます。'
    fee_card = root.xpath('//article[contains(@class,"fee-card")][2]/p[not(contains(@class,"fee"))]')[0]
    fee_card.text = '企業・自治体・大学・スタートアップなど。有料・無料の区分と役割を確認して参加します。'
    fee_note = root.get_element_by_id('main_ch05').xpath('.//div[@class="chapter-body"]/p[@class="note"]')[0]
    for old in root.xpath('//*[@id="fee-rules-reference"] | //p[contains(text(),"会費年度・途中入会・入退会の運用は")]'):
        old.getparent().remove(old)
    fee_note.addnext(node(f'<p class="note" id="fee-rules-reference">会費年度・途中入会・入退会の運用は、<a href="{doclink("rules", "rules_ch02")}">規約の「未決・提案」</a>として協議します。</p>'))
    for nav in root.xpath('//nav[contains(@class,"founding-doc-nav")]'):
        nav.getparent().remove(nav)
    top = root.xpath('//div[@class="book-top"]')[0]
    top.addprevious(node(docnav('main')))
    last = root.get_element_by_id('main_ch07').xpath('.//div[@class="chapter-body"]')[0]
    for old in last.xpath('./div[@class="document-links"]'):
        last.remove(old)
    last.append(node(related(['members', 'rules', 'secretariat'])))
    add_common_style(root)
    save(path, root)
    return root


def members_sections():
    founders = table(['区分', '期待する役割', '状況'], [
        [escape(x['name']) + ('（募集中）' if x['name'] == '県内各自治体' else ''),
         escape(x['role']), escape(x['status'])] for x in DATA['founder_groups']], '0.23,0.49,0.28')
    officers = table(['役職', '候補', '状況'], [[escape(x['position']), escape(x['name']),
                         '<span class="approval-tag">了承待ち</span>'] for x in DATA['officers']], '0.25,0.52,0.23')
    membership = table(['会費区分', '年会費', '議決権'], [
        ['有料企業会員', '10万円', 'あり'],
        ['無料会員', '0円', '原則なし。企画提案・意見交換・個別案件への参加は可能'],
        ['発起人団体・事務局団体', '会費区分を別途確認', '会費にかかわらず1団体1票']
    ], '0.27,0.20,0.53')
    return [
        ('発起人の構成', '発起人は、<br>この5区分から。', '県・自治体・企業・団体と、立ち上げを一緒に進めます。',
         founders + '<p class="key-message">自治体の個別名は、<strong>参画と掲載の了承を確認してから</strong>掲載します。</p><p>この一覧は発起人構成の提案です。正式参画済みの団体一覧ではありません。</p>'),
        ('役員候補', '共同代表と事務局長を、<br>関係者と協議する。', '候補者・所属組織への確認を経て、役職・権限を確定します。',
         officers + '<p class="note">副知事の個人名は指定していません。候補掲載は就任了承を示すものではありません。</p><div class="working-team"><span class="eyebrow">実務事務局</span><strong>TCO・MDL</strong><p>トヨタカローラ大分・モビリティデザインラボ</p></div><p>県・おおいたプラットに、日常の事務局業務や専任の工数拠出を求めません。</p>'),
        ('会員名簿と参加区分', '参加を確認し、<br>名簿を育てる。', '正式な会員名は、入会と掲載了承の確認後に追加します。',
         '<p>企業は有料・無料の区分で参加。自治体・大学・スタートアップなども無料で参加できる提案です。</p>' + membership +
         '<p><strong>発起人として正式参画する自治体も、無料で1団体1票。</strong>複数の立場を兼ねても票は増えません。</p><p>組織名の掲載可否・役割・会費区分・議決権を事務局が確認します。担当者の個人連絡先は公開しません。</p>' + related(['main', 'rules', 'secretariat']))
    ]


def rules_sections():
    fees = table(['項目', '運用のたたき台'], [
        ['会費年度', '4月1日〜翌年3月31日。初年度は設立日（目標：2027年1月26日）〜2027年3月31日'],
        ['途中入会', '有料会員は入会月から年度末まで月割り。10万円×対象月数÷12で計算し、1円未満を切り捨てる'],
        ['納付', '入会承認・請求から30日以内を基本。税の取扱いは請求方法と併せて確認する'],
        ['区分の変更', '事務局への申出を受け、運営会議で確認。原則、次年度から適用する'],
        ['未納', '事務局が本人と事情・納付見通しを確認。解消しない場合は、運営会議で会員継続・区分変更等を判断する']
    ], '0.22,0.78')
    return [
        ('総則と会員', '何のための団体か。<br>誰が、どう参加するか。', '本規約は協議用の条文案です。発足時の承認を経て施行します。',
         article(1, '名称・組織形態', '<p>名称を「大分未来モビリティ・コンソーシアム」とし、法人格を持たない任意団体として設立する。設立は2027年1月26日を目標とする。</p>') +
         article(2, '目的・活動', f'<p>{escape(DATA["purpose"])}</p><p>地域課題の共有、人材育成、共同案件の企画、関係者の接続、実施・実証計画の具体化、結果の共有・発信を行う。</p><p><a href="{doclink("main", "pvmv")}">PVMVと設立趣意を読む →</a></p>') +
         article(3, '会員', '<p>趣旨に賛同する企業・自治体・大学・団体等が、組織単位で参加する。企業は有料・無料の区分で参加できる。自治体・大学・スタートアップ等の無料参加も設ける。</p><p>人材育成プログラムへの参加は、入会・会費とは別に、誰でも無料とする。個別案件への参加は各団体が選ぶ。</p>') +
         article(4, '会費と権利', '<p>有料企業会員の年会費は10万円。無料会員も企画提案・意見交換・個別案件に参加できる。</p><p>有料企業会員・事務局団体・発起人団体は、会費にかかわらず1団体1票。一般の無料会員は原則として議決権を持たない。複数の立場を兼ねても票は増えない。</p>')),
        ('会費と入退会', '参加の手続きと、<br>費用の扱いをそろえる。', 'この章の具体的な運用は「未決・提案」です。設立に向けて協議し、確定します。',
         proposal('第5条｜入会・区分変更', '<p>入会希望を事務局が受け付け、趣旨・規約への同意、会費区分、役割、連絡担当、組織名の掲載可否を確認する。運営会議の承認後、名簿へ登録する。</p><p>区分変更は事務局への申出を受け、運営会議で確認する。発起人・事務局の議決権は、会費区分の変更のみでは失わない。</p>') +
         proposal('第6条｜会費年度・納付・未納', fees) +
         proposal('第7条｜退会・除名', '<p>退会は事務局への申出で受け付け、申出月の末日を退会日とする。既納会費は原則返還しない提案とし、既に合意した個別案件の契約・精算は別に確認する。</p><p>規約違反、活動の重大な妨げ、機密の不適切な公表等は、事実確認と本人の説明機会を設けたうえで、運営会議で除名等の対応を判断する。</p>')),
        ('役員と意思決定', '決める場は、<br>運営会議に一本化。', '日常の実務を事務局が担い、組織全体と個別プロジェクトの判断を同じ会議で行います。',
         article(8, '役員・事務局', '<p>共同代表と事務局長を置く。共同代表は方針の共有・対外説明を担い、事務局長は日常の調整と会議準備を統括する。実務事務局はTCO・MDLとする。</p><p>運営会議で決める事項や各団体の契約・支出承認を、役員が単独で代替しない。</p><p class="rule-note"><span class="unsettled-tag">未決・提案</span> 選任・交代手続、任期、対外的な署名権限の詳細は設立前に協議する。</p>') +
         article(9, '運営会議', '<p>意思決定の会議体は運営会議（仮称）一つとし、月1回を基本とする。全体方針・規約・会員制度・共通予算と、個別プロジェクトを扱う。</p><p>議決権は1団体1票。代理出席を認め、欠席し代理もいない場合はその回の投票を行わない。TCO・MDLを、案件への関与だけを理由に議決から一律に除外しない。</p><p class="rule-note"><span class="unsettled-tag">未決・提案</span> 定足数・可決条件・同数時・書面議決の扱いは未確定。設立に向けて協議し、本条を確定する。</p>') +
         article(10, '案件の採択・認定', '<p>登録→検討開始の承認→具体化→最終決定→実行・報告の順に進める。提案は口頭でも資料でもよく、枚数・様式は義務化しない。</p><p>個別案件では検討開始を「採択」、条件が整った実施計画の最終判断を「認定」とする。全体の事項も同じ会議体・同じ流れで扱い、事務局が決定事項を記録する。</p>')),
        ('実行・情報・会計', '実行の責任と、<br>共有の範囲を明確に。', '団体の共通運営と、個別の開発・実証・運行は分けて管理します。',
         article(11, '個別案件の責任', '<p>実行・契約・費用・安全管理・保険等は、各案件の参加主体が合意して担う。コンソーシアムの認定は、各団体の契約・支出承認、行政の許可、安全性の保証を代替しない。</p>') +
         article(12, '秘密保持・発信', '<p>機密情報・個人情報は必要な関係者に限定し、必要に応じ案件単位で秘密保持契約等を結ぶ。採択後は、公表範囲を確認したうえで「検討中のプロジェクト」として発信できる。検討中・認定・実行済みを区別する。</p>') +
         proposal('第13条｜成果物・データの取扱い', '<p>持ち込まれた既存の知的財産・資料等は、従前の権利者の権利を尊重する。共同成果の帰属・利用・公表、データの利用目的・共有先・管理・費用は、着手前に参加主体間で合意する。入会だけで権利や利用許可を自動的に移転しない。</p>') +
         article(14, '共通運営の会計', '<p>共通運営の契約・口座・会計管理はMDLが通常事業と区分して担い、運営会議へ収支を報告する。初年度はTCOの持ち出しを基本に予算を協議する。負担額・上限・期間は未決で、無制限の負担や支出承認済みの資金として扱わない。</p>') +
         proposal('第15条｜改定・解散・残余財産', '<p>規約の改定と解散は運営会議で決定する。適用する議決条件は第9条の協議で確定する。</p><p>解散時は債権債務と原契約・交付条件を確認して精算し、返還等が必要な資金を処理する。残余財産の処分先・方法は運営会議で決定し、最終収支を報告する。</p>') +
         '<p class="note">附則｜本規約は、設立時の承認を経て施行する。現時点で候補者・関係団体の承認や支払義務が生じたことを示さない。</p>' + related(['main', 'members', 'secretariat']))
    ]


def secretariat_sections():
    duties = table(['業務', '実務担当', '確認・承認'], [
        ['企画・会議準備', 'TCO・MDL', '事務局長が調整し、運営会議へ提示'],
        ['案件調整・参加者対応', 'TCO・MDL', '関係する自治体・企業・団体と具体化'],
        ['活動報告・発信', 'TCO・MDL', '関係者と公表範囲・表現を確認'],
        ['契約・入金・支払・記帳', 'MDL', '負担団体の社内承認と、MDL側の会計確認'],
        ['収支・活動の報告', 'TCO・MDL', '運営会議へ報告']
    ], '0.28,0.22,0.50')
    budget = table(['費用', '見積もる基準'], [
        ['企画・調整・会議準備', '必要人員×稼働時間×単価'],
        ['会議・交流の実費', '会場・備品・必要回数の見積'],
        ['発信・資料・会員対応', '制作・更新・対応の業務量'],
        ['会計・外部サービス等', '契約・請求・記帳・利用料の見積']
    ], '0.35,0.65')
    payments = table(['段階', '担当のたたき台', '残す記録'], [
        ['支出申請', '業務担当者がMDLの会計担当へ提出', '目的・金額・負担先・予算との対応'],
        ['予算・内容確認', 'TCO・MDLの事務局', '共通運営費か個別案件費かを確認'],
        ['承認', '費用負担団体の社内承認者', '各団体の承認記録。未承認の負担を約束しない'],
        ['契約・支払', '契約主体とMDLの会計担当', '契約・請求・支払の証憑'],
        ['記帳・確認', 'MDLの記帳担当と別の確認担当', '帳簿・証憑・入出金の対応'],
        ['報告', 'TCO・MDL', '月次の確認と運営会議への収支報告']
    ], '0.18,0.38,0.44')
    return [
        ('役割分担', '日常の実務は、<br>TCO・MDLが担う。', '県・おおいたプラットには、後押しと仲間づくりをお願いします。',
         duties + '<p class="key-message">県・おおいたプラットに、<strong>日常の事務局業務や専任人員・運営工数の拠出を求めません。</strong></p><p>県側の連絡窓口とコンソーシアムの実務事務局は区別します。個別案件に参加する場合の役割・負担は、その案件で別に協議します。</p>'),
        ('初年度予算', '無償奉仕にせず、<br>運営を続ける予算を組む。', '初年度は会費だけでは賄えない想定です。TCOの持ち出しを基本に運営予算を協議します。',
         budget + '<div class="fund-card"><h3>必要経費と財源を、同じ表で確認</h3><p>会費は年10万円×有料会員数を基準に、年度・途中入会の扱いを反映して見積もります。会員数・収入額は未確定です。</p><p>協賛・活用可能な補助事業は、獲得状況を区別します。不足分とTCOの負担額・上限・期間は、確定した財源と併せて協議します。</p></div><p><span class="unsettled-tag">未決・提案</span> 業務量・単価・初年度予算総額・TCO負担額・上限・期間・社内承認方法。数値を置いて支出承認済みと扱いません。</p><p>会費収入の範囲だけに活動を一律に限定せず、必要な業務と財源を組み合わせます。支出に先立ち負担主体と資金の見通しを確認します。</p>'),
        ('契約・口座・入出金', '契約する主体と、<br>確認する担当をそろえる。', '共通運営の会計と個別プロジェクトの会計を分けます。以下は具体的な運用のたたき台です。',
         proposal('共通運営の契約・口座', '<p>共通運営の契約主体はMDLを基本とし、委託範囲・費用負担・承認者を各契約で明確にする。個別案件は、その案件の参加主体が契約する。</p><p>MDLが管理する専用口座の利用を第一案とし、開設可否と実際の名義を金融機関・経理と確認する。MDLの通常事業と専用の管理区分・台帳を分ける。</p>') +
         proposal('入金・支出・記帳・確認', payments) +
         '<p>運営会議の決定と、負担団体の契約・支出承認を分けます。予算・契約・社内決裁の範囲内で実務を進め、範囲を超える事項は運営会議へ戻して確認します。</p>' + related(['main', 'members', 'rules']))
    ]


def section_html(key, n, count, sec):
    label, title, lead, body = sec
    links = (f'<a href="#{key}_ch{n-1:02}" rel="prev">← 前のページ</a>' if n > 1 else '') + \
        '<a href="#reader-toc">目次へ戻る</a>' + \
        (f'<a href="#{key}_ch{n+1:02}" rel="next">次のページ →</a>' if n < count else '')
    return f'<section class="reader-section" id="{key}_ch{n:02}" data-chapter="{n}"><header class="chapter-head"><div class="chapter-kicker"><span class="page-no">{n:02}</span><span class="chapter-label">{label}</span></div><h2>{title}</h2><p class="lead">{lead}</p></header><div class="chapter-body">{body}</div><div class="page-foot"><span>{DATA["name"]}</span><b>{n:02} / {count:02}</b></div><nav aria-label="{n} / {count} ページの案内" class="section-navigation">{links}</nav></section>'


def build_document(doc, sections, main_root):
    # Reuse the existing reader's exact style and unchanged entry scripts.
    root = html.fromstring(markup(main_root))
    head = markup(root.find('head'))
    head = re.sub(r'<title>.*?</title>', f'<title>{escape(doc["title"])}｜大分未来モビリティ</title>', head)
    toc = ''.join(f'<li><a href="#{doc["key"]}_ch{n:02}"><span>{n:02}｜{escape(sec[0])}</span><span class="toc-page">{n} / {len(sections)}</span></a></li>' for n, sec in enumerate(sections, 1))
    content = ''.join(section_html(doc['key'], n, len(sections), sec) for n, sec in enumerate(sections, 1))
    notice = '候補者・関係団体の了承を示すものではありません。未決の条項は「未決・提案」と表示し、設立に向けて協議します。'
    if doc['key'] == 'rules':
        notice += '本規約は発足時の承認を経て施行します。'
    body = f'''<body><aside class="draft-strip" aria-label="資料の取扱い"><div><strong>関係者向け</strong><span>TCO・MDLからの提案資料</span></div><nav aria-label="資料メニュー"><a href="{BASE}guide/">資料一覧</a><a href="{BASE}read/main/">構想説明書</a><a data-entry-reset href="{BASE}?entry=1">入口へ</a></nav></aside><a class="skip" href="#book-content">本文へ移動</a><header class="site-head reader-head"><a class="brand" href="{BASE}"><b class="brand-mark" aria-hidden="true">O.</b><span>大分未来モビリティ・<br>コンソーシアム<small>OITA MIRAI MOBILITY CONSORTIUM</small></span></a><div class="header-side"><span class="header-context">設立に向けた4つの文書</span><span class="private-tag">関係者外秘</span><a href="{BASE}guide/">資料一覧へ</a></div></header>{docnav(doc['key'])}<div class="book-top"><div class="eyeline"><span>FOUNDING DOCUMENT {doc['number']} / 04</span><span>2026.10.28 更新</span></div><h1>{escape(doc['title'])}</h1><p class="lead">{escape(doc['summary'])}</p><p class="notice"><strong>協議用の提案</strong>｜{notice}</p><p class="publication-update"><strong>設立目標：{TARGET}</strong></p><div class="book-actions"><a href="#reader-toc">目次から読む ↓</a><a class="founding-pdf-link" href="{BASE}{doc['pdf']}?v={VERSION}">同じ内容のPDF</a><a href="{BASE}guide/">4文書の一覧 →</a></div></div><nav class="book-tools" aria-label="資料内の移動"><a href="#reader-toc">↑ 目次へ</a><a href="{BASE}guide/">資料一覧</a><a href="{doclink('main')}">構想説明書へ →</a></nav><main class="book-body" id="book-content"><nav class="reader-toc" id="reader-toc" aria-label="本文の目次"><h2>この文書で確認すること。</h2><ol class="chapter-toc">{toc}</ol></nav><article class="reader-document" lang="ja">{content}</article><nav class="book-end" aria-label="読み終わった後"><a href="#reader-toc">↑ 目次へ戻る</a>　/　<a href="{BASE}guide/">資料一覧へ</a></nav></main><footer class="site-foot"><div><strong>{DATA['name']}</strong><p>実務事務局：トヨタカローラ大分・モビリティデザインラボ</p></div><div class="foot-code">FOUNDING DOCUMENT {doc['number']} / 04<br>2026.10.28</div></footer></body>'''
    target = ROOT / doc['path'] / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('<!DOCTYPE html>\n<html lang="ja">' + head + body + '</html>\n')


def update_guide():
    path = ROOT / 'guide/index.html'
    root = html.fromstring(path.read_text())
    overview = root.get_element_by_id('overview')
    overview.get_element_by_id('overview-title').text = '設立に必要な、4つの文書。'
    overview.xpath('./p[@class="intro"]')[0].text = '構想を共有し、参加者を確かめ、ルールと実務を整える。2027年1月26日の設立を目標に、4文書を一緒に確認します。'
    grid = overview.xpath('./div[@class="document-grid"]')[0]
    grid.clear(); grid.set('class', 'document-grid')
    for d in DOCS:
        card = f'<article class="document"><div><p class="eyebrow">FOUNDING DOCUMENT / {d["number"]}</p><h2><b>{d["number"]}</b><span>{escape(d["title"])}</span></h2><p>{escape(d["summary"])}</p><p class="pdf-meta" data-pdf-key="{d["key"]}">Web版とPDFを同期</p></div><div class="document-actions"><a class="primary-link" href="{doclink(d["key"])}">Webで読む →</a><a class="download-link" href="{BASE}{d["pdf"]}?v={VERSION}" download>同じ内容のPDFをダウンロード</a></div></article>'
        grid.append(node(card))
    for old in overview.xpath('./div[@class="reference-document"]'):
        overview.remove(old)
    overview.append(node(f'<div class="reference-document"><h3>別紙｜参考候補と根拠資料</h3><p>145の参考候補。正式な参画者名簿とは区別します。</p><a href="{BASE}read/annex/">別紙をWebで読む →</a><a href="{BASE}documents/annex.pdf?download=1" download>別紙PDF（参考版）</a></div>'))
    position = root.get_element_by_id('position')
    position.xpath('./p')[0].text = '4文書はいずれも協議用の提案です。候補者の就任、発起人・会員の正式参画、未決条項の承認を示しません。設立目標は2027年1月26日。Web本文と各PDFを同じ内容にそろえています。'
    root.get_element_by_id('consultation').xpath('./p[last()]/a')[0].set('href', doclink('members'))
    root.get_element_by_id('consultation').xpath('./p[last()]/a')[0].text = '発起人・会員・役員名簿を見る →'
    add_common_style(root)
    save(path, root)


def sync_related():
    for rel in ['index.html', 'concept/index.html']:
        path = ROOT / rel
        r = html.fromstring(path.read_text())
        blocks = r.xpath('//*[@id="founder-base"]')
        if blocks:
            f = blocks[0]
            f.xpath('./h3')[0].text = '発起人は、この5区分で。'
            ul = f.xpath('./ul')[0]; ul.clear(); ul.set('class', 'founder-names')
            for group in DATA['founder_groups']:
                title = group['name'] + ('（募集中）' if group['name'] == '県内各自治体' else '')
                ul.append(node(f'<li>{escape(title)}<small>{escape(group["status"])}</small></li>'))
            p = f.xpath('./p[last()]')[0]
            p.clear(); p.text = '発起人構成の提案です。各自治体の個別名は、参画と掲載の了承を確認してから掲載します。'
            p.append(node(f'<a href="{doclink("members")}">発起人・会員・役員名簿 →</a>'))
        for t in r.xpath('//time[@datetime="2027-01" or @datetime="2027-01-26"]'):
            t.set('datetime', '2027-01-26'); t.text = '2027.01.26'
            li = t.getparent()
            strong = li.xpath('./div/strong')
            if strong: strong[0].text = 'コンソーシアム設立を目指す'
            p = li.xpath('./div/p')
            if p: p[0].text = '設立目標。参画意向・規約・運営体制を協議し、正式な設立は関係者の合意を経て決めます。'
        for a in r.xpath('//a[contains(@href,"/guide/")]'):
            if '構想説明書' in a.text_content() and len(a.text_content()) < 70:
                a.text = '構想・名簿・規約・事務局の4文書 →'
        add_common_style(r); save(path, r)
    # Only sync explicit formation-goal wording, never unrelated task deadlines.
    for path in ROOT.rglob('*.html'):
        text = path.read_text()
        text = text.replace('2027年1月の正式発足', f'{TARGET}の正式発足')
        text = text.replace(f'{TARGET}を目標とする正式発足', f'{TARGET}の正式発足')
        text = text.replace('2027年1月 設立目標', f'{TARGET} 設立目標')
        text = text.replace('2027年1月の設立を目標', f'{TARGET}の設立を目標')
        text = re.sub(r'\?v=20261028-(?:proposal1|consistency2)', '?v=' + VERSION, text)
        path.write_text(text)


def build():
    main = sync_main()
    factories = {'members': members_sections, 'rules': rules_sections, 'secretariat': secretariat_sections}
    for doc in DOCS[1:]:
        build_document(doc, factories[doc['key']](), main)
    update_guide()
    sync_related()
    print('Four founding documents synchronized; target:', TARGET)


def build_fonts(variable_path):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools import subset
    paths = [ROOT / d['path'] / 'index.html' for d in DOCS] + [ROOT / x for x in ['organization/index.html', 'guide/index.html', 'index.html', 'concept/index.html']]
    text = ''.join(html.fromstring(p.read_text()).text_content() for p in paths)
    for name, weight in [('regular', 400), ('black', 900)]:
        font = instantiateVariableFont(TTFont(variable_path), {'wght': weight}, inplace=True)
        options = subset.Options()
        options.flavor = 'woff'
        options.notdef_glyph = options.notdef_outline = options.recommended_glyphs = True
        sub = subset.Subsetter(options=options)
        sub.populate(text=text)
        sub.subset(font)
        font.flavor = 'woff'
        font.save(ROOT / f'read/main/assets/proposal-jp-{name}.woff')
        print('Font:', name, len(font.getBestCmap()), 'characters')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--font-variable', type=Path, help='Local full Noto Sans JP variable font for rebuilding subsets')
    args = parser.parse_args()
    build()
    if args.font_variable:
        build_fonts(args.font_variable)
