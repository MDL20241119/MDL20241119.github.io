#!/usr/bin/env python3
"""Generate three blank, one-page A4 forms and compatible legacy URL aliases."""
from __future__ import annotations
import hashlib,json
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

BASE=Path(__file__).resolve().parents[2]
OUTPUT=BASE/'documents'
FONTDIR=BASE/'read/main/assets'
W,H,PAD=595.276,841.89,34
WIDTH=W-PAD*2
INK,BLUE,LINE,MUTED=map(HexColor,['#102e53','#edf2f8','#afc2d8','#526476'])
NAME='大分未来モビリティコンソーシアム'
VERSION='20261108-minimal-forms'
# label, writing-space height, short cue; policies remain in the shared rules.
FORMS=[
 dict(key='participants',title='参加申込・承諾書',
 intro='参加・役割の承諾を、この1枚で確認します。該当する欄だけ記入してください。',
 rows=[
 ('団体・代表者',49,''),
 ('担当・連絡先',49,''),
 ('参加区分',43,'□有料（年10万円）  □無料　免除は規約・決定に従う'),
 ('引き受ける役割',56,'団体：□発起人  □事務局\n本人：□共同代表  □事務局長　□上記の役割なし'),
 ('就任する本人',49,'氏名・所属／就任日・任期（役職に就く場合）'),
 ('目的・協力内容',62,'取り組みたいこと・持ち寄れる強み'),
 ('確認・承諾',96,'規約の版：\n設立趣旨・規約と、選んだ役割に同意します。役職は選任後に就任し、業務・対価・権限は合意した範囲とします。\n団体名の公開：□可  □要相談　条件・留保：'),
 ('団体の承諾者',48,'役職・氏名／承諾日（団体の権限者が記入）'),
 ('本人の就任承諾',48,'本人の署名・記名／承諾日（役職に就く場合）'),
 ('事務局記入',60,'承認日・記録番号／区分・会費・議決権')],
 note='記入後は事務局へ提出し、非公開で保管します。個別案件の費用・契約は別途合意します。',
 aliases=['membership-application','membership-application-print','consent-founder','consent-representative','consent-secretariat','consent-secretariat-chief']),
 dict(key='project-sheet',title='プロジェクトシート',
 intro='提案から実施・振り返りまで、同じ1枚に追記します。',
 rows=[
 ('案件名・番号',44,'更新日：'),
 ('提案者・責任者',56,'提案団体／実施主体・責任者／連絡先'),
 ('課題・狙い',65,'誰の、何を変えるか'),
 ('実施計画',83,'やること・場所・時期／協力者と役割／目標・確かめ方'),
 ('費用・負担',62,'総額・財源・負担者／契約主体／運営会計・案件会計の区分'),
 ('実施条件',79,'安全・保険・許認可・権利・データの扱い／未解決事項・担当・期限'),
 ('①検討着手',48,'採択・保留・見送り／決定日・運営記録番号'),
 ('②実施計画',48,'認定・保留・見送り／決定日・運営記録番号'),
 ('結果・次の行動',65,'実績・費用・課題／継続・変更・終了／担当・期限')],
 note='提案者は自治体・企業等。採択は検討開始の判断です。認定後も実施条件を整えて実行します。',
 aliases=['project-proposal','project-proposal-print','project-implementation','project-implementation-print']),
 dict(key='operations-record',title='運営・決定記録',
 intro='設立・運営会議の決定と、計画・予算をまとめて記録します。',
 rows=[
 ('会議・記録番号',48,'日時・方法／議長・記録者'),
 ('参加・議決権',59,'参加団体・代理等／対象団体数・参加数／利益相反・除外'),
 ('議題・決定①',69,'議題・文書名／版・日付／決定内容・賛否／条件・担当・期限'),
 ('議題・決定②',69,'議題・文書名／版・日付／決定内容・賛否／条件・担当・期限'),
 ('計画・予算',89,'活動・担当・時期／運営収入（会費・TCO負担等）と支出・上限／案件別予算は区分'),
 ('契約・会計',89,'契約主体・協定名／版／MDLの受託範囲・代理権／支出承認者・上限／口座名義・資金帰属／支払・照合担当'),
 ('残る対応',65,'確認事項・担当・期限／次回の判断'),
 ('記録の確認',62,'共同代表・関係者の確認者／確認日／保管先')],
 note='設立時は規約・役員・計画・予算・正式設立日を記録します。契約・許認可は必要な手続を別途行います。',
 aliases=['founding-meeting','founding-meeting-print','annual-plan-budget','annual-plan-budget-print','administration-agreement-review','administration-agreement-review-print'])
]

def prepare_fonts(directory):
 required=str(FORMS)+NAME+'協議用様式A4・1枚0123456789 /'
 for label,weight in [('JP','regular'),('JP-Bold','black')]:
  f=SourceFont(FONTDIR/f'proposal-jp-{weight}.woff')
  missing={c for c in set(required)-set(map(chr,f.getBestCmap())) if not c.isspace() and ord(c)>127}
  if missing:raise ValueError(f'{weight}: missing glyphs: '+''.join(sorted(missing)))
  f.flavor=None;p=Path(directory)/f'forms-{weight}.ttf';f.save(p)
  pdfmetrics.registerFont(TTFont(label,str(p)))
 pdfmetrics.registerFontFamily('JP',normal='JP',bold='JP-Bold',italic='JP',boldItalic='JP-Bold')

def paragraph(c,text,x,top,width,size=10,leading=15,bold=False,color=INK,max_height=None):
 style=ParagraphStyle('form',fontName='JP-Bold' if bold else 'JP',fontSize=size,leading=leading,textColor=color,wordWrap='CJK')
 p=Paragraph(escape(text).replace('\n','<br/>'),style);_,height=p.wrap(width-size,H)
 if max_height is not None and height>max_height:raise ValueError(f'Text overflows: {text} ({height}>{max_height})')
 p.drawOn(c,x,top-height);return height

def build(form,number,date):
 path=OUTPUT/(form['key']+'.pdf');c=Canvas(str(path),pagesize=(W,H),pageCompression=1,invariant=1)
 c.setTitle(form['title']);c.setAuthor('トヨタカローラ大分・モビリティデザインラボ')
 c.setFillColor(HexColor('#ffffff'));c.rect(0,0,W,H,fill=1,stroke=0)
 paragraph(c,NAME,PAD,H-27,WIDTH,9,13,True)
 c.setFillColor(INK);c.setFont('JP-Bold',10);c.drawRightString(W-PAD,H-38,f'{number:02} / 03')
 paragraph(c,form['title'],PAD,H-57,WIDTH,27,35,True)
 paragraph(c,form['intro'],PAD,H-102,WIDTH,10,15)
 top=H-132
 for label,height,cue in form['rows']:
  bottom=top-height
  if bottom<54:raise ValueError('Not enough writing space: '+form['key'])
  c.setStrokeColor(LINE);c.setLineWidth(.6);c.setFillColor(BLUE);c.rect(PAD,bottom,104,height,fill=1,stroke=1)
  c.setFillColor(HexColor('#ffffff'));c.rect(PAD+104,bottom,WIDTH-104,height,fill=1,stroke=1)
  paragraph(c,label,PAD+9,top-10,94,10.5,16,True,max_height=height-14)
  if cue:paragraph(c,cue,PAD+114,top-9,WIDTH-124,9.5,15,color=MUTED,max_height=height-14)
  top=bottom
 paragraph(c,form['note'],PAD,top-13,WIDTH,8.5,13)
 c.setStrokeColor(LINE);c.line(PAD,32,W-PAD,32)
 paragraph(c,'協議用様式 / '+date.replace('-','.')+' / A4・1枚',PAD,25,WIDTH,8,11,color=MUTED)
 c.showPage();c.save();return path

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 policy=json.loads((OUTPUT/'founding.json').read_text());mp=OUTPUT/'document-manifest.json';manifest=json.loads(mp.read_text());records=[];aliases={}
 with TemporaryDirectory() as temp:
  prepare_fonts(temp)
  for number,form in enumerate(FORMS,1):
   p=build(form,number,policy['updated']);records.append(dict(key=form['key'],title=form['title'],pdf='documents/'+p.name,pages=1,sha256=digest(p),use=form['intro']))
   # Existing direct URLs serve the integrated sheet, never the obsolete form.
   for name in form['aliases']:
    target=OUTPUT/(name+'.pdf');target.write_bytes(p.read_bytes());aliases['documents/'+target.name]='documents/'+p.name
   print(p)
 manifest.update(forms_version=VERSION,establishment_forms=records,consent_forms=[],form_aliases=aliases)
 mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
