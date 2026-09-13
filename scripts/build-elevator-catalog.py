"""Build the four-page summary, rider guide, and combined role catalog.

Usage: python scripts/build-elevator-catalog.py --regular-font PATH --bold-font PATH
Driver/admin PDFs retain the existing, source-checked four-page guides.
"""
from pathlib import Path
import argparse
from io import BytesIO
import fitz
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/catalogs'
ASSET = ROOT / 'assets/cases/yoko-elevator'
PHOTO = ASSET / 'user-flow.jpg'
INK = '#13253E'; MUTED = '#4D5C6C'; PAPER = '#FAFBFD'
BLUE = '#163EE4'; ORANGE = '#B94416'; GREEN = '#006D61'; LIME = '#E8FB65'
URL = 'https://mobilitydlab.com/danchi-elevator/'
args = argparse.ArgumentParser()
args.add_argument('--regular-font', required=True)
args.add_argument('--bold-font', required=True)
args = args.parse_args()
pdfmetrics.registerFont(TTFont('JP', args.regular_font))
pdfmetrics.registerFont(TTFont('JPB', args.bold_font))

def rect(x,y,w,h,color):
    c.setFillColor(HexColor(color)); c.rect(x,H-y-h,w,h,fill=1,stroke=0)
def line(x,y,x2,y2,color='#CAD2DE',width=.7):
    c.setStrokeColor(HexColor(color)); c.setLineWidth(width); c.line(x,H-y,x2,H-y2)
def text(s,x,y,size=12,bold=False,color=INK):
    c.setFont('JPB' if bold else 'JP',size); c.setFillColor(HexColor(color)); c.drawString(x,H-y-size,s)
def para(s,x,y,w,size=12,color=INK,leading=None,bold=False):
    p=Paragraph(s,ParagraphStyle('p',fontName='JPB' if bold else 'JP',fontSize=size,leading=leading or size*1.6,textColor=HexColor(color),wordWrap='CJK'))
    _,h=p.wrap(w,1500); p.drawOn(c,x,H-y-h); return h
def pic(path,x,y,w,h):
    c.drawImage(ImageReader(str(path)),x,H-y-h,width=w,height=h,preserveAspectRatio=True,anchor='c',mask='auto')
def panel(n,x,y,w):
    # Viewport placement of the unmodified supplied photograph.
    bounds=[(50,259,344,615),(411,259,343,585),(769,259,347,585),(1135,259,349,584)]
    sx,sy,sw,sh=bounds[n]; scale=w/sw; h=sh*scale
    c.saveState(); clip=c.beginPath(); clip.rect(x,H-y-h,w,h); c.clipPath(clip,stroke=0)
    c.drawImage(ImageReader(str(PHOTO)),x-sx*scale,H-y-(874-sy)*scale,width=1536*scale,height=874*scale)
    c.restoreState(); return h
def common(n,label,role='要約版',accent=BLUE):
    rect(0,0,W,H,PAPER); rect(0,0,W,8,accent)
    text('MOBILITY DESIGN LAB',M,24,10,True)
    text('横のエレベーター',M,43,9,False,MUTED)
    text(label,W-240,25,9,True,accent); line(M,66,W-M,66)
    line(M,H-40,W-M,H-40)
    text('MOBILITY DESIGN LAB / 2026.09.13',M,H-28,7.5,False,MUTED)
    text(f'{role}   {n:02d} / 04',W-144,H-29,8,True,accent)
def title(lines,y=89,size=33):
    for i,s in enumerate(lines): text(s,M,y+i*size*1.25,size,True)
def foot(s,y=None): para(s,M,y or H-66,W-2*M,8,MUTED,12)
def start(path,size,title_):
    global c,W,H,M
    W,H=size; M=36 if W<600 else 32
    c=canvas.Canvas(str(path),pagesize=size,pageCompression=1)
    c.setTitle(title_); c.setAuthor('株式会社モビリティデザインラボ')
    c.setSubject('横のエレベーター｜実画面でわかるサービスと操作')

# RIDER: four A4 pages. The supplied photo is kept intact in the first page.
start(OUT/'yoko-elevator-user.pdf',(595,842),'横のエレベーター｜ユーザー用')
common(1,'01 / ユーザー用','ユーザー用')
title(['まちを、','エレベーターのように。'],91,36)
para('買い物へ。公民館へ。いつもの暮らしの場所へ。<br/>必要なときに呼び出して、決められた乗降場所の間を移動します。',M,195,523,12)
rect(M,251,523,39,LIME); text('アルファードなど、一般的な乗用車を活用。',M+14,260,14,True)
pic(PHOTO,M,309,523,298)
para('提供写真：ユーザーアプリの流れ。車種・地名・画面は掲載時の例です。',M,613,523,8,MUTED,12)
for i,(a,b) in enumerate([('呼ぶ','乗る場所・降りる場所・<br/>人数を選ぶ。'),('待つ','車の確定通知と<br/>待つ場所を確認。'),('乗る','迎えの車を確認して乗車。<br/>帰りも改めて呼び出す。')]):
    x=M+i*178; line(x,646,x+167,646); text(str(i+1).zfill(2),x,656,17,True,BLUE);text(a,x+36,656,17,True);para(b,x,687,162,10.5)
rect(M,739,523,43,'#EEF1FF');para('地域の乗降場所をつなぐ乗合サービスです。<br/>運行エリア・日時・料金・利用条件は、地域の案内をご確認ください。',M+12,747,498,9,leading=14)
c.showPage()

common(2,'01 / ユーザー用','ユーザー用');title(['場所と人数を選び、','「OK」で依頼。'],90,33)
para('地域の案内するLINEなどから、利用画面を開きます。<br/>初回の登録方法は、地域の案内をご確認ください。',M,185,523,11)
for n,(a,b) in enumerate([('乗降場所・人数を選ぶ','地図で乗る場所、降りる場所を選び、<br/>一緒に乗る人数を入力します。'),('内容を確認して依頼','出発・到着・人数を確認。<br/>正しければ「OK」を押します。')]):
    x=M+n*271; text(f'0{n+1}',x,243,22,True,BLUE);text(a,x+40,250,13,True)
    panel(n,x+4,290,235);para(b,x,722,249,11,leading=18)
foot('画面例：グリーンプラザ → 看護科学大学・1人。地名やボタン表記は提供版によって異なります。',777)
c.showPage()

common(3,'01 / ユーザー用','ユーザー用');title(['迎えの車と、','待つ場所を確かめる。'],90,33)
para('依頼したら、車が決まったことを確認。<br/>待つ場所を写真で確かめてから、乗降場所へ向かいます。',M,185,523,11)
for i,(a,b) in enumerate([('車の確定通知を見る','「車が確定しました！」を確認。<br/>迎えの車の写真・車両名を確かめます。'),('乗降場所を写真で確認','周辺の建物や目印を確かめ、<br/>指定した乗降場所で待ちます。')]):
    x=M+i*271;text(f'0{i+3}',x,243,22,True,BLUE);text(a,x+40,250,13,True);panel(i+2,x+4,290,235);para(b,x,703,249,11,leading=18)
rect(M,755,523,32,LIME);text('車の確定通知は、車が到着したというお知らせではありません。',M+10,764,10,True)
c.showPage()

common(4,'01 / ユーザー用','ユーザー用');title(['いつもの移動も、','困ったときも。'],90,33)
para('よく使う経路は、次から選びやすく。帰りも改めて呼び出します。',M,184,523,11)
tips=[('お気に入り・履歴','よく使う経路を登録。<br/>次回は経路を選び、<br/>内容を確認して依頼。'),('帰りは「入替」','出発と到着を入れ替え、<br/>内容を確認して依頼。<br/>帰りは自動予約されません。'),('待つ場所の確認','停留所の写真で、<br/>周囲の目印を確認。<br/>不明なときは運営窓口へ。')]
for i,(a,b) in enumerate(tips):
    x=M+i*178;rect(x,226,166,128,'#EEF1FF');text(a,x+10,239,12,True,BLUE);para(b,x+10,270,146,10,leading=18)
qas=[('乗らなくなったら？','画面のキャンセル表示と地域のルールを確認し、取り消し操作または運営窓口への連絡を行います。'),('車が来ない・会えないときは？','乗降場所と確定した車両を再確認。解決しないときは運営窓口へ連絡します。'),('スマホ操作が難しいときは？','電話受付などの利用支援は地域によって異なります。運営窓口へご相談ください。'),('車いす・大きな荷物は？','利用できる車両や介助の範囲を、呼び出す前に運営窓口へ確認してください。')]
for i,(a,b) in enumerate(qas):
    x=M+(i%2)*271;y=384+(i//2)*109;line(x,y,x+250,y);text(a,x,y+10,11,True);para(b,x,y+34,249,10,leading=17)
rect(M,621,523,140,'#EEF1FF');text('この地域のご利用案内',M+13,633,14,True);text('配布する運営者が記入',386,638,8,False,MUTED)
for i,label in enumerate(['運行日・時間','料金・利用条件','運営窓口・電話','最寄りの乗降場所']):
    x=M+13+(i%2)*255;y=670+(i//2)*42;text(label,x,y,9,False,MUTED);line(x,y+29,x+232,y+29)
foot('掲載画面は資料提供時の例です。地域の最新の運行案内・操作方法をご確認ください。',775)
c.save()

# SUMMARY: four landscape pages, one clear purpose per page.
start(OUT/'danchi-elevator-catalog.pdf',(842,595),'横のエレベーター｜要約版')
common(1,'SERVICE / サービス概要');title(['横の','エレベーター'],90,44)
text('その一歩を、もっと気軽に。',M,218,21,True)
para('買い物や地域の集まりへ。<br/>必要なときに呼び出して、決められた<br/>乗降場所の間を移動する乗合サービス。',M,270,358,13,leading=23)
rect(M,365,362,74,LIME);para('アルファードなど、一般的な乗用車で<br/>地域の日常の移動を支えます。',M+15,382,332,14,bold=True,leading=23)
pic(PHOTO,420,113,390,222);para('実際の利用者画面 / 提供写真',420,343,390,8,MUTED)
roles=[('01 ユーザー','呼ぶ・待つ・乗る',BLUE),('02 ドライバー','迎える・運ぶ・確かめる',ORANGE),('03 管理者','見る・記録する・改善する',GREEN)]
for i,(a,b,col) in enumerate(roles):
    y=375+i*43;line(420,y,810,y);text(a,420,y+8,11,True,col);text(b,558,y+8,11)
para('富士見ヶ丘団地（大分市）での導入事例を掲載。<br/>2025年度実証：運行10日 / 実利用72人 / 延べ342回乗車',M,465,366,10,MUTED,17)
foot('運行エリア・日時・料金・車両は地域によって異なります。掲載画面・実証記録は現在の運行状況を示すものではありません。',524)
c.showPage()
common(2,'01 USER / ユーザー用');text('4つの実画面で、操作を確認。',M,81,23,True)
pic(PHOTO,M,116,778,423)
c.showPage()
common(3,'02 DRIVER / ドライバー用',accent=ORANGE);title(['迎えに行く。乗車を確かめる。'],84,28)
para('画面の操作は、安全な場所に停車してから。',M,128,778,12)
pic(ASSET/'driver-screen.png',M,178,440,298)
para('元マニュアルのドライバー画面 / 表示例',M,485,440,8,MUTED)
for i,(a,b) in enumerate([('準備してログイン','運行エリア・ドライバー・車両を選ぶ。'),('呼び出しを引き受ける','処理待ちを確認し、運行順に沿って移動。'),('到着を知らせ、乗車を確認','停車後に「到着通知」。人数・行き先を確認。'),('降車を確認して完了','実際に降りたことを見て「降車」を操作。')]):
    x=497;y=172+i*80;line(x,y,810,y);text(str(i+1).zfill(2),x,y+10,20,True,ORANGE);text(a,x+37,y+13,13,True);para(b,x+37,y+39,272,10.5,leading=17)
foot('満車・不在・通信不良の対応と、運行前後の確認は詳細版へ。実際の運行ルール・待機時間は運営者が定めます。',524)
c.showPage()
common(4,'03 ADMIN / 管理者用',accent=GREEN);title(['運行を見て、次の改善へ。'],84,28)
para('利用者の待ち状況と車両の動きを、ひとつの画面で確認。',M,128,778,12)
pic(ASSET/'admin-screen.png',M,177,410,318)
para('元マニュアルの管理画面 / 数値・車両情報は表示例',M,501,410,8,MUTED)
for i,(a,b) in enumerate([('いまの運行を見る','待ち人数・車両位置・引き受け状況を照合。'),('日報・月報で振り返る','日付・月を選択し、更新してPDFへ出力。'),('現場の声と合わせて改善','待ち時間・不在・満車の理由を確認する。')]):
    x=469;y=179+i*84;line(x,y,810,y);text(str(i+1).zfill(2),x,y+8,21,True,GREEN);text(a,x+41,y+13,14,True);para(b,x+41,y+43,294,11,leading=18)
rect(469,450,341,60,LIME);text('地域への導入・アプリ開発のご相談',483,460,12,True);text('info@mobilitydlab.com',483,484,12,True)
c.linkURL('mailto:info@mobilitydlab.com',(469,H-510,810,H-450),relative=0)
foot('MDLの導入支援：課題把握 → 乗降場所・運行設計 → アプリを現場で検証 → 改善。  mobilitydlab.com/danchi-elevator/',524)
c.linkURL(URL,(32,H-540,810,H-521),relative=0)
c.save()

# Combine the four-page role booklets with stable local URLs and PDF bookmarks.
all_pdf=fitz.open()
for role in ['user','driver','admin']:
    with fitz.open(OUT/f'yoko-elevator-{role}.pdf') as d: all_pdf.insert_pdf(d)
all_pdf.set_metadata({'title':'横のエレベーター｜詳細版・ユーザー用／ドライバー用／管理者用','author':'株式会社モビリティデザインラボ','subject':'実画面でわかる操作と運用・各4ページ／全12ページ'})
all_pdf.set_toc([[1,'01 ユーザー用',1],[1,'02 ドライバー用',5],[1,'03 管理者用',9]])
all_pdf.save(OUT/'yoko-elevator-detail.pdf',garbage=4,deflate=True)
with fitz.open(OUT/'danchi-elevator-catalog.pdf') as d:
    for i,page in enumerate(d):
        pix=page.get_pixmap(matrix=fitz.Matrix(1.7,1.7))
        buffer=BytesIO()
        Image.frombytes('RGB',[pix.width,pix.height],pix.samples).save(buffer,format='WEBP',quality=91,method=6)
        assert buffer.tell()>0
        (ROOT/f'assets/cases/danchi-catalog-{i+1}.webp').write_bytes(buffer.getvalue())
for name in ['danchi-elevator-catalog','yoko-elevator-user','yoko-elevator-driver','yoko-elevator-admin','yoko-elevator-detail']:
    p=OUT/f'{name}.pdf'
    with fitz.open(p) as d: print(name,len(d),'pages',p.stat().st_size,'bytes')
