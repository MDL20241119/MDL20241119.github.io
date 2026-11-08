#!/usr/bin/env python3
"""Build blank establishment forms from the reviewed public policy below.

Run after build_documents.py. Uses the same bundled Japanese fonts; writes
normal/print PDFs and records page counts and hashes in document-manifest.json.
No external inputs, filled records, signatures, or transmission are involved.
"""
from __future__ import annotations
import hashlib
import json
import re
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from fontTools.ttLib import TTFont as SourceFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

BASE = Path(__file__).resolve().parents[2]
OUTPUT = BASE / 'documents'
FONTDIR = BASE / 'read/main/assets'
W, H, PAD = 595.276, 841.89, 28
WIDTH = W - PAD * 2
INK, BLUE, LINE, PAPER, WHITE = map(HexColor, ['#102e53', '#e8f0fc', '#afc2d8', '#f2f5f7', '#ffffff'])
NAME = '大分未来モビリティコンソーシアム'
DRAFT = '正式決定前の様式案です。記入・確認・決議前の空欄を含み、この文書だけで正式な合意や承認を示すものではありません。'


def section(title, paragraphs, fields):
    return {'title': title, 'paragraphs': paragraphs, 'fields': fields}

FORMS = [
    {
        'key': 'membership-application', 'title': '入会申込と会員区分確認',
        'intro': '入会を希望する団体が記入し、事務局が区分・了承状況を確認するための様式です。申込み、入会承認、公開掲載の了承を分けて記録します。設立前は申込準備として扱います。',
        'sections': [
            section('申込団体と参加の目的', [
                '県・市町村・企業・大学・NPO等が、それぞれの課題や強みを持ち寄ることを基本とします。個人情報は必要な範囲に限り、連絡先は内部管理します。',
                '共創の7ヶ条は、対等・実践・挑戦・改善・多様性・行動力・共感です。課題、技術、人材、現場、紹介、実行などの貢献を持ち寄ります。'
            ], [
                '申込日／団体名／団体区分：', '団体の申込権限を確認した者・確認方法：',
                '担当窓口の氏名・所属・業務用連絡先（内部管理）：', '参加の目的・地元の課題・関心テーマ：',
                '持ち寄れる強み・活動・協力できる範囲：'
            ]),
            section('希望区分と費用の確認', [
                '企業等は年会費10万円の有料区分と無料区分から希望を示します。自治体・大学・NPO等は無料です。無料の人材育成プログラムへの参加は、会員加入と別に扱います。',
                '有料団体の議決権と正式な発起人・事務局団体の例外を分けて確認し、1団体1票とします。発起人の免除期間・初年度徴収・税務は、承認した規約と決定記録に従います。',
                '個別プロジェクトの開発・車両・運行等の費用は会費と別に合意します。加入だけで車両提供や実証実施を確約しません。'
            ], [
                '希望区分：有料／無料／区分相談',
                '発起人・事務局としての申請：なし／あり（別途承諾書・承認記録：　）',
                '適用規約の版・会費年度・承認済み徴収条件：', '申込団体が確認した内容・確認日：'
            ]),
            section('事務局の確認と入会承認', [
                '事務局が正式参画の意思と権限、会員区分を確認し、運営会議の入会承認を記録してから名簿へ反映します。規約採用前の受付を正式加入と表示しません。',
                '団体名・ロゴ・担当者名等の公開了承は入会承認と別に確認します。記入済み申込書・連絡先・確認資料は、公開する空欄様式と分けて保管します。'
            ], [
                '受付番号／受付日／確認担当：', '確認結果：準備中／追加確認／入会審議へ／取下げ',
                '入会承認日・会議記録番号・承認条件：', '承認後の区分・議決権の根拠・適用開始日：',
                '公開してよい項目・媒体・了承者・了承日：', '名簿反映日／申込団体への結果通知日／内部保管先：'
            ])
        ]
    },
    {
        'key': 'project-proposal', 'title': '案件提案と検討着手の審議',
        'intro': '県・市町村・企業等の提案主体が持ち込む課題と企画を受け付け、ステップ02で企画検討に着手するか判断する様式です。口頭提案も事務局が記録でき、様式の利用を提案条件にはしません。',
        'sections': [
            section('提案主体から案件を受け付ける', [
                '提案するのは、課題や実行を担う県・市町村・企業等です。TCO・MDLは記録と具体化を支援し、提案主体に代わってコンソーシアム自らの企画として扱いません。'
            ], [
                '案件番号／受付日／案件名：', '提案主体・担当窓口（業務用連絡先は内部管理）：',
                '対象エリア・対象者／誰のどの課題を改善したいか：', '課題の根拠・現場の声・現在の状況：',
                '提案内容・希望時期／既に行っていること：'
            ]),
            section('検討する価値と協力を整理する', [
                '二本柱は、e-Palette計6台を活用するサービス企画・実証と、トヨタグループによる大分での自動運転実証を目指す構想です。サービス企画・アプリ開発・データ分析を共通の支援基盤とします。利用や実施は案件ごとに条件を確認します。',
                '事務局は提案主体と、地元の必要性、共創の意義、参加意思、必要工数・費用、支援可能な範囲を整理します。課題の改善に必要な方法を検討します。'
            ], [
                '主な領域：e-Palette／自動運転／共通基盤／その他（　）',
                '提案者が担う役割・持ち寄る現場や資源：', '協力候補と了承状況／必要な支援：',
                '検討段階の工数・費用・負担者・利用できる資源：', '事前に確認する権利・安全・許認可・公開範囲：'
            ]),
            section('ステップ02で検討着手を決議する', [
                '運営会議は企画検討に着手するかを決議します。採択は実施承認ではありません。採択後は検討中のプロジェクトとして扱い、03で具体化し、同じ運営会議の04認定を経て実行へ進めます。',
                '議決要件、票数、利益相反の扱いは承認した規約に従い、無回答を賛成に数えません。条件と次の行動を記録します。'
            ], [
                '会議日・議案番号／適用規約・議決方法：',
                '議決権保有団体・出席／代理／書面参加・利益相反の扱い：',
                '結果：採択／継続検討／見直し／採択しない（賛成・反対・棄権：　）',
                '判断理由・条件・異論と対応：', '具体化の担当・成果物・工数上限・次回判断時期：',
                '提案主体への通知・公開してよい範囲：'
            ])
        ]
    },
    {
        'key': 'project-implementation', 'title': '実施計画と認定及び実施前確認',
        'intro': 'ステップ02で採択した案件を具体化し、04の認定と05の実行前確認につなぐ様式です。認定、当事者の契約・社内承認、許認可、安全上の実施条件を別々に確認します。',
        'sections': [
            section('ステップ03で実施計画を具体化する', [
                'TCO・MDLが提案主体・実施主体と計画を具体化します。実行責任は個別に合意した参加主体が担い、非参加団体に費用や責任を生じさせません。'
            ], [
                '案件番号・計画版／02採択日・記録番号：', '提案主体／実施責任者／参加主体と了承状況：',
                '対象者・対象エリア・課題／実施するサービスと作業：', '実施期間・場所・工程・各工程の責任者：',
                '車両・人員・技術・アプリ・データ分析の支援範囲と条件：',
                '予算・財源・負担主体・契約主体／コンソーシアム運営と個別案件の会計区分：'
            ]),
            section('実装に必要な条件と評価をそろえる', [
                '成果指標は実施後に判断したいことから逆算し、現状値、測定方法、対象期間、目標、判断時期を案件ごとに決めます。利用者数と延べ利用回数、目標と実績を分けます。',
                'サンリオ連携車等の条件がある案件は、県の後援判断と利用許諾の対象・用途・表現を確認します。コンソーシアム認定で代替せず、他案件へ一律に適用しません。'
            ], [
                '成果指標ごとの現状値・目標・単位・測定方法・判断日：',
                '許認可・場所／車両の使用条件・後援／利用許諾と確認先：',
                '安全管理責任者・事故／苦情時の連絡体制・中止条件・保険：',
                '扱う情報・取得目的・権利帰属・利用／公開範囲・保存方法：',
                '未解決条件・解消担当・確認期限／継続・変更・終了の判断方法：'
            ]),
            section('ステップ04で実施計画を認定する', [
                '運営会議は、計画・責任・負担・条件を確認して認定を判断します。条件付き継続検討を、実行を許可した認定と読み替えません。正式な認定範囲と未解決事項を議事録へ残します。'
            ], [
                '会議日・議案番号／適用規約・議決方法：', '出席・議決権・利益相反の整理／賛成・反対・棄権：',
                '結果：認定／条件付き継続検討／見直し／中止', '認定した計画版・範囲・予算／判断理由・留保事項：',
                '結果通知先・通知日／公表可能な説明：'
            ]),
            section('ステップ05の実施前確認と結果報告', [
                '実施責任者が必要条件の充足を確認し、事務局が認定計画との整合を確認します。未解決の必須条件があれば実施を先行させません。実施後は事実・結果・課題を報告し、継続、修正又は終了を判断します。'
            ], [
                '契約・社内承認・許認可・保険・権利等の証拠と確認者：', '実施可否・実施開始日／未解決事項・停止判断：',
                '計画変更の有無／追加承認・再審議の記録：', '実績・評価結果・事故／苦情・費用実績／報告日：',
                '次の判断・担当・期限／公表する成果と権利確認：'
            ])
        ]
    },
    {
        'key': 'founding-meeting', 'title': '設立会議の議案と合意記録',
        'intro': '設立時会合又は書面合意の準備と記録に使う様式です。開催前は議案、開催後は確認された議決結果を記入します。未記入欄や候補者名を承認・就任の証拠にせず、署名・確認日は実際の日付を記録します。',
        'sections': [
            section('会合と参加権限を確認する', [
                '設立日は関係者の合意で決めます。設立時会合は設立合意を残す手続であり、新たな常設委員会を置きません。設立後の常設会議体は運営会議一つとします。',
                '参加主体が進行・合意方法を確認します。未施行の規約を説明や合意なく適用せず、無回答を同意と数えません。'
            ], [
                '会合名／開催日時・場所・オンライン又は書面の方法：', '議長・記録担当／合意した進行方法・意思確認方法：',
                '参加団体・正式参画の了承状況／出席者・代理権限・書面回答：',
                '事前共有資料の名称・版・共有日／欠席・未回答・留保：'
            ]),
            section('設立に必要な議案をそろえる', [
                '各議案に対象文書の版と承認を求める内容を示します。候補者の了承、発起人認定、会費免除、役職選任、公開掲載は別々に確認します。',
                '共同代表は県副知事とTCO本田常務、事務局長はMDL CEO佐藤氏とする体制案です。本人・所属団体の了承と選任を経て、任期・権限を記録します。'
            ], [
                '議案1　設立趣旨・PVMV・正式設立日／資料版・提案内容：', '議案2　規約・会費・議決方法／未決条件と採用内容：',
                '議案3　発起人・会員・共同代表・事務局長／了承と選任：',
                '議案4　初年度事業計画・年間計画・ロードマップ・予算：',
                '議案5　事務局業務・対価・代表権限・契約と会計管理方法：',
                '議案6　初回運営会議・残る確認事項と担当：'
            ]),
            section('議案ごとの結果と留保を記録する', [
                '以下を議案ごとに記入します。継続協議は可決に含めず、条件付き了承は条件と発効時点を明確にします。許認可、銀行の受入、各社の支出決裁は別途確認します。'
            ], [
                '議案番号・対象文書の版：', '結果：承認／条件付き了承／継続協議／否決／取下げ',
                '意思確認の方法・賛否・留保／利益相反と扱い：', '決定内容・適用日・条件／異論と対応：',
                '残る確認事項・担当・期限／次の判断時期：'
            ]),
            section('記録を確認し保管する', [
                '記録担当が共同代表及び各承認主体に内容を確認し、承認された版を保管します。原本・署名・連絡先・個別の証拠は内部管理し、対外版には了承された範囲だけを掲載します。'
            ], [
                '記録作成者・作成日／確認した各主体・確認日：', '修正内容・最終確定版／確認未了の部分：',
                '承認済み添付資料一覧・保管先：', '公開する要旨・掲載了承／会員への通知日：'
            ])
        ]
    },
    {
        'key': 'annual-plan-budget', 'title': '初年度事業計画と収支予算',
        'intro': '事務局が、設立時に承認する初年度の活動とコンソーシアム運営予算をまとめる様式です。コンソーシアム運営と個別プロジェクトの会計を分け、未承認の負担や収入を確定額にしません。',
        'sections': [
            section('対象期間と実施する活動', [
                '正式設立日と会計年度は設立時に決めます。現行案は2027年1月26日を設立目標とし、初年度を正式設立日から2027年3月31日までとしています。目標日を実際の設立日として記録しません。',
                'e-Paletteサービスと自動運転実証の二本柱を、サービス企画・アプリ開発・データ分析で支えます。運営会議、会員対応、提案主体による案件の登録・採択・具体化、活動と会計の報告を計画します。'
            ], [
                '計画名・版／対象年度・開始日・終了日：', '目的・初年度に整える状態／次年度につなぐ成果：',
                '活動別の担当・実施期間・成果物・確認指標：',
                '案件一覧と状態（提案／採択／具体化／認定／実施／終了）：',
                '年度内の会議・報告・点検時期／事業量と支援上限：'
            ]),
            section('収支と財源を分けて積算する', [
                '事務局業務は業務量・単価・実費から積算します。会費10万円の税務区分、初年度徴収、発起人の免除期間は承認内容に従います。仮算は正式見積や発注額として転記しません。',
                'コンソーシアム運営と個別プロジェクトの会計を分け、同じ作業・経費・期間の二重計上を防ぎます。基本運営費はTCOが負担する方針とし、額・上限の社内承認と運営予算の承認を分けます。'
            ], [
                '収入別：会費・TCO負担・協賛等／計画額・確定額・根拠・入金時期：',
                '支出別：業務・工数・単価・実費／予算額・根拠・支払時期：',
                '各収支の運営／個別プロジェクト区分・期間・財源・重複照合：',
                '運営費合計／確実な充当額／不足額／TCO承認額と上限：',
                '資金不足時の縮小・延期・予算変更方針：'
            ]),
            section('承認と実績管理', [
                '設立時会合で初年度計画・予算を承認し、その後の変更は運営会議に付議します。共同代表は決定に基づいて執行を確認し、事務局が実績を報告します。各社の社内承認は別途必要です。',
                '2026年度に組織・人材・企画を整え、2027年度に条件の整った案件を実行・検証し、2028年度以降の継続運営・事業化を判断する案です。補助事業のKPI・期限は最終交付条件と照合します。'
            ], [
                '承認日・会議記録番号／承認した計画と予算の版：',
                'TCO等の負担承認記録／事務局業務・報酬の合意記録：',
                '計画額・実績額・差異・未収未払・次回修正内容：',
                '補助事業の適用版・期限・KPI・成果物・検収条件：',
                '次年度計画の検討時期・責任者／変更承認履歴：'
            ])
        ]
    },
    {
        'key': 'administration-agreement-review', 'title': '契約と会計管理の協定確認案',
        'intro': 'TCO・MDLと共同代表候補が、契約・会計管理の協定に盛り込む条件を確認する文書です。法律・税務・銀行の確認を経て、当事者が正式な協定と権限を定めます。',
        'sections': [
            section('管理対象と契約上の立場を決める', [
                '新法人は設けず、MDLを契約・取引実務の窓口とする構想です。契約ごとに、MDL自身の契約、団体の代理署名、契約事務の支援のどれを担うかを明確にします。',
                'コンソーシアム運営は合意した委任範囲内でMDLが、個別プロジェクトは各実施主体が契約・支払を担います。会計を分け、団体・構成員の連帯責任を自動的な前提にしません。'
            ], [
                '協定当事者・締結権限の確認方法／対象期間：', '契約ごとの主体・名義・署名者・代理権の根拠：',
                '対象資金・業務／コンソーシアム運営と個別案件の範囲・除外範囲：',
                '責任分担・未承認の契約や債務を防ぐ方法：'
            ]),
            section('業務と対価・承認権限を定める', [
                'TCO・MDLが日常運営を担い、事務局長が統括します。おおいたプラット・行政には仲間づくりや課題共有等を相談します。専任人員や日常運営工数の拠出を前提にしません。',
                '支出申請、承認、支払、記帳、照合を分けます。共同代表は合意した権限内で執行を確認し、MDLの自己報酬をMDLだけで最終承認しません。TCO負担分はTCOの社内承認も確認します。'
            ], [
                '業務項目・担当・成果物・報告頻度・支援工数：', '業務対価・実費・精算条件／見積と承認の根拠：',
                '申請者・承認者・支払担当・記帳担当・独立した照合担当：',
                '契約・支出の権限と上限／予算超過・利益相反時の扱い：',
                'TCO負担額・上限・社内承認／予算変更と停止の手続：'
            ]),
            section('資金と情報を分けて管理する', [
                '大分銀行にMDL名義のコンソーシアム用口座を設ける方法を相談します。口座名義、資金帰属、銀行の受入、税務上の扱いを確認し、必要な承認後に実行します。',
                'MDL固有資金と分け、コンソーシアム運営・個別案件の帳簿、証憑、期間、財源を照合します。連絡先、了承記録、口座情報は内部管理します。'
            ], [
                '銀行への相談結果・受入条件／資金帰属と区分方法：',
                '入出金権限・残高照合・未収未払・月次報告の方法：',
                '証憑の保存責任者・保存期間・閲覧権限・引継ぎ方法：',
                '秘密情報・個人情報・成果物の扱い／公開前確認：',
                '法律・税務・銀行の確認事項・担当・回答日・残件：'
            ]),
            section('終了と正式合意に備える', [
                '終了・解除時は未払・未収、預かり資金、進行中契約、データ・証憑を整理します。未合意の保証や立替義務を追加せず、返還・引継ぎ条件を協定で定めます。',
                '当事者と専門家が確認した後、正式協定を作成します。運営会議の内部承認と当事者による契約締結は別に記録します。'
            ], [
                '協定の見直し・終了条件／事前通知と変更手続：',
                '残金・債権債務・契約・記録の返還及び引継ぎ条件：',
                '未解決の法務・税務・銀行条件／対応担当・期限：',
                '正式協定を作成する担当・確認者／内部承認と締結の記録：'
            ])
        ]
    }
]

CONSENTS = [
    {
        'key': 'consent-founder', 'title': '発起人承諾書', 'band': '発起人としての参画',
        'statement': '当団体は、大分未来モビリティコンソーシアムの設立趣旨に賛同し、下記の確認書類・条件に基づき、発起人として参画することを承諾します。',
        'fields': [('法人・団体名', ''), ('承諾者の役職・氏名', ''), ('確認書類', '設立趣意書・規約等の文書名／版／日付：'), ('参画に関する確認事項', '会費等の条件・留保事項（ある場合）：')],
        'note': '発起人としての参画を確認する書類です。個別プロジェクトの参加・費用負担・契約、名称等の公開範囲は、別途確認します。'
    },
    {
        'key': 'consent-representative', 'title': '共同代表就任承諾書', 'band': '共同代表としての就任',
        'statement': '私は、大分未来モビリティコンソーシアムの目的及び下記の確認書類・条件を確認し、所定の選任手続を経た上で、共同代表に就任することを承諾します。',
        'fields': [('所属・所属先での役職', ''), ('氏名', ''), ('就任する役職', '共同代表'), ('就任日・任期', '就任日：　　　年　　月　　日　　任期：'), ('確認書類・条件', '規約等の版／日付・選任記録・留保事項：')],
        'note': '本書は就任の承諾を確認するものであり、選任の決定記録は別途作成します。契約権限・費用負担等は、承認済みの規約・決議・個別合意の範囲に従います。'
    },
    {
        'key': 'consent-secretariat', 'title': '事務局引受承諾書', 'band': '法人・団体による事務局の引受け',
        'statement': '当団体は、大分未来モビリティコンソーシアムの目的に賛同し、下記の確認書類・担当範囲・条件に基づき、事務局業務を引き受けることを承諾します。',
        'fields': [('法人・団体名', ''), ('承諾者の役職・氏名', ''), ('担当業務・役割分担', '対象業務・役割分担書の名称／版：'), ('開始日・期間', '開始日：　　　年　　月　　日　　期間：'), ('対価・費用等の合意', '協定・契約等の名称／日付・留保事項：')],
        'note': '事務局長個人の就任承諾とは別の書類です。契約・会計管理の委任、予算、対価・費用負担は別途合意した範囲に限り、本書だけで包括的な権限や負担を設定しません。'
    },
    {
        'key': 'consent-secretariat-chief', 'title': '事務局長就任承諾書', 'band': '事務局長としての就任',
        'statement': '私は、大分未来モビリティコンソーシアムの目的及び下記の確認書類・条件を確認し、所定の選任手続を経た上で、事務局長に就任することを承諾します。',
        'fields': [('所属・所属先での役職', ''), ('氏名', ''), ('就任日・任期', '就任日：　　　年　　月　　日　　任期：'), ('確認書類・担当範囲', '規約・役割分担等の版／日付：'), ('その他の確認事項', '選任記録・兼務・留保事項（ある場合）：')],
        'note': '本書は個人の就任承諾です。所属団体の事務局業務の引受け、対価・費用負担・契約権限は別途合意します。'
    }
]


def prepare_fonts(directory):
    # Preserve the exact font family used by the canonical documents.
    required = ''.join(str(x) for x in [FORMS, CONSENTS]) + NAME + DRAFT + '設立協議用清書版この書類の流れ各項目を押すと該当ページへ目次へ戻る承諾日署名記名御中年月日0123456789OITA / FOUNDING DOCUMENTS（ドラフト）→'
    for label, weight in [('JP', 'regular'), ('JP-Bold', 'black')]:
        font = SourceFont(FONTDIR / f'proposal-jp-{weight}.woff')
        missing = set(required) - set(chr(cp) for cp in font.getBestCmap())
        missing = {c for c in missing if not c.isspace() and ord(c) > 127}
        if missing:
            raise ValueError(f'{weight}: missing glyphs: ' + ''.join(sorted(missing)))
        font.flavor = None
        path = Path(directory) / f'forms-{weight}.ttf'
        font.save(path)
        pdfmetrics.registerFont(TTFont(label, str(path)))
    pdfmetrics.registerFontFamily('JP', normal='JP', bold='JP-Bold', italic='JP', boldItalic='JP-Bold')


def para(canvas, text, x, top, width, size=11, leading=18, bold=False, color=INK):
    style = ParagraphStyle('forms', fontName='JP-Bold' if bold else 'JP', fontSize=size,
                           leading=leading, textColor=color, wordWrap='CJK')
    paragraph = Paragraph(escape(text).replace('\u3000', '&#160;&#160;&#160;&#160;'), style)
    # CJK hanging punctuation can extend by one glyph; reserve that space.
    _, height = paragraph.wrap(width - size, H)
    paragraph.drawOn(canvas, x, top - height)
    return top - height


def furniture(canvas, title, page, date, print_mode):
    canvas.setFillColor(WHITE if print_mode else PAPER)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont('JP-Bold', 8)
    canvas.drawString(PAD, H - 26, NAME)
    canvas.drawRightString(W - PAD, H - 26, '（ドラフト）')
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(.5)
    canvas.line(PAD, 37, W - PAD, 37)
    canvas.setFont('JP', 7.5)
    canvas.drawString(PAD, 21, title)
    canvas.drawRightString(W - PAD, 21, f'{date.replace("-", ".")}  /  {page:02}')


def cover(canvas, form, date, print_mode):
    furniture(canvas, form['title'], 1, date, print_mode)
    canvas.bookmarkPage('contents')
    canvas.addOutlineEntry('目次', 'contents', 0)
    canvas.setFillColor(INK)
    canvas.roundRect(PAD, H - 238, WIDTH, 189, 4, fill=1, stroke=0)
    para(canvas, 'OITA  /  FOUNDING DOCUMENTS', PAD + 17, H - 65, WIDTH - 34, 10, 15, True, LINE)
    para(canvas, form['title'], PAD + 17, H - 98, WIDTH - 34, 28, 37, True, WHITE)
    y, m, d = map(int, date.split('-'))
    para(canvas, f'設立協議用清書版  /  {y}年{m}月{d}日', PAD + 17, H - 211, WIDTH - 34, 9, 14, False, LINE)
    cursor = para(canvas, form['intro'], PAD, H - 255, WIDTH, 11, 18) - 20
    cursor = para(canvas, 'この書類の流れ', PAD, cursor, WIDTH, 25, 32, True) - 8
    n = len(form['sections'])
    height = min(118, (cursor - 118 - 8 * (n - 1)) / n)
    for i, section in enumerate(form['sections'], 1):
        bottom = cursor - height
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(LINE)
        canvas.roundRect(PAD, bottom, WIDTH, height, 3, fill=1, stroke=1)
        canvas.setFillColor(BLUE)
        canvas.rect(PAD, bottom, 67, height, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont('JP-Bold', 28)
        canvas.drawCentredString(PAD + 33.5, bottom + height / 2 - 10, f'{i:02}')
        para(canvas, section['title'], PAD + 81, bottom + height / 2 + 15, WIDTH - 147, 16, 23, True)
        canvas.setFont('JP-Bold', 11)
        canvas.drawRightString(W - PAD - 15, bottom + height / 2 - 4, f'{i+1:02} →')
        canvas.linkRect('', f'section-{i}', (PAD, bottom, W - PAD, cursor), thickness=0)
        cursor = bottom - 8
    para(canvas, '各項目を押すと該当ページへ移動します。', PAD, 94, WIDTH, 8.5, 13)
    para(canvas, DRAFT, PAD, 74, WIDTH, 8, 12)
    canvas.showPage()


def content_page(canvas, form, section, number, date, print_mode):
    furniture(canvas, form['title'], number + 1, date, print_mode)
    canvas.bookmarkPage(f'section-{number}')
    canvas.addOutlineEntry(section['title'], f'section-{number}', 0)
    canvas.setFillColor(BLUE)
    canvas.roundRect(PAD, H - 132, 77, 77, 3, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont('JP-Bold', 43)
    canvas.drawCentredString(PAD + 38.5, H - 111, f'{number:02}')
    para(canvas, section['title'], PAD + 96, H - 61, WIDTH - 96, 24, 33, True)
    cursor = H - 150
    for text in section['paragraphs']:
        cursor = para(canvas, text, PAD, cursor, WIDTH, 11, 18) - 8
    cursor -= 7
    available = cursor - 54
    row_height = available / len(section['fields'])
    if row_height < 50:
        raise ValueError('Insufficient writing space: ' + form['key'] + '/' + str(number))
    for label in section['fields']:
        bottom = cursor - row_height
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.5)
        canvas.rect(PAD, bottom, WIDTH, row_height, fill=1, stroke=1)
        label_style = ParagraphStyle('label', fontName='JP-Bold', fontSize=10.5, leading=15.5, textColor=INK, wordWrap='CJK')
        label_p = Paragraph(escape(label), label_style)
        _, label_height = label_p.wrap(WIDTH - 24, H)
        strip = max(31, label_height + 12)
        canvas.setFillColor(BLUE)
        canvas.rect(PAD + .25, cursor - strip, WIDTH - .5, strip - .25, fill=1, stroke=0)
        label_p.drawOn(canvas, PAD + 12, cursor - 7 - label_height)
        cursor = bottom
    canvas.setFillColor(INK)
    canvas.setFont('JP-Bold', 8)
    canvas.drawString(PAD, 43, '← 目次へ戻る')
    canvas.linkRect('', 'contents', (PAD, 40, PAD + 85, 53), thickness=0)
    canvas.showPage()


def build_form(form, date, print_mode):
    suffix = '-print' if print_mode else ''
    path = OUTPUT / (form['key'] + suffix + '.pdf')
    canvas = Canvas(str(path), pagesize=(W, H), pageCompression=1, invariant=1)
    canvas.setTitle(form['title'])
    canvas.setAuthor('トヨタカローラ大分・モビリティデザインラボ')
    cover(canvas, form, date, print_mode)
    for number, page in enumerate(form['sections'], 1):
        content_page(canvas, form, page, number, date, print_mode)
    canvas.save()
    return path


def build_consent(form):
    path = OUTPUT / (form['key'] + '.pdf')
    canvas = Canvas(str(path), pagesize=(W, H), pageCompression=1, invariant=1)
    canvas.setTitle(form['title'])
    canvas.setAuthor('トヨタカローラ大分・モビリティデザインラボ')
    margin, width = 51, W - 102
    canvas.setFillColor(WHITE)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    para(canvas, NAME, margin, H - 55, width, 11, 16, True)
    para(canvas, form['title'], margin, H - 97, width, 27, 36, True)
    canvas.setFillColor(INK)
    canvas.rect(margin, H - 178, width, 31, fill=1, stroke=0)
    para(canvas, form['band'], margin + 6, H - 152, width - 12, 11, 18, True, WHITE)
    para(canvas, NAME + '　御中', margin, H - 197, width, 11, 18)
    canvas.setFillColor(INK)
    canvas.setFont('JP', 11)
    canvas.drawRightString(W - margin, H - 238, '承諾日：　　　　年　　月　　日')
    cursor = para(canvas, form['statement'], margin, H - 264, width, 11, 26) - 20
    row_height = min(58, (cursor - 224) / len(form['fields']))
    for label, hint in form['fields']:
        bottom = cursor - row_height
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.5)
        canvas.setFillColor(BLUE)
        canvas.rect(margin, bottom, 133, row_height, fill=1, stroke=1)
        canvas.setFillColor(WHITE)
        canvas.rect(margin + 133, bottom, width - 133, row_height, fill=1, stroke=1)
        para(canvas, label, margin + 5, cursor - 6, 122, 10, 16, True)
        if hint:
            para(canvas, hint, margin + 138, cursor - 6, width - 143, 9, 16)
        cursor = bottom
    cursor = para(canvas, '署名／記名：', margin, cursor - 20, width, 11, 18, True) - 16
    para(canvas, form['note'], margin, cursor, width, 9, 18)
    para(canvas, NAME + '｜' + form['title'], margin, 48, width, 8, 12)
    canvas.showPage()
    canvas.save()
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    policy = json.loads((OUTPUT / 'founding.json').read_text())
    date = policy['updated']
    manifest_path = OUTPUT / 'document-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    form_records, consent_records = [], []
    with TemporaryDirectory() as temp:
        prepare_fonts(temp)
        for form in FORMS:
            normal = build_form(form, date, False)
            printable = build_form(form, date, True)
            form_records.append({'key': form['key'], 'title': form['title'], 'pdf': 'documents/' + normal.name,
                'pages': len(form['sections']) + 1, 'sha256': digest(normal),
                'print_pdf': 'documents/' + printable.name, 'print_pages': len(form['sections']) + 1,
                'print_sha256': digest(printable)})
            print(normal)
            print(printable)
        for consent in CONSENTS:
            path = build_consent(consent)
            consent_records.append({'title': consent['title'], 'pdf': 'documents/' + path.name,
                'pages': 1, 'sha256': digest(path)})
            print(path)
    manifest['establishment_forms'] = form_records
    manifest['consent_forms'] = consent_records
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
