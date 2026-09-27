"""Build a self-contained HTML deck from content.json.
Usage: python render.py --font /path/to/NotoSansJP.ttf --qa /tmp/catalog-qa
Dependencies for authoring only: Pillow, fonttools, markdown, budoux; cairosvg for optional QA.
"""
import argparse, base64, html, io, json, math, re
from pathlib import Path
from PIL import ImageFont
from fontTools.ttLib import TTFont
from fontTools import subset
import budoux

ap=argparse.ArgumentParser();ap.add_argument('--font',required=True);ap.add_argument('--qa');a=ap.parse_args()
BASE=Path(__file__).resolve().parent; DOC=json.loads((BASE/'content.json').read_text())
SLIDES=DOC['slides']; RAW=DOC['raw_records']; PAGE={s['key']:s['no'] for s in SLIDES}
BLUE='#1976D2'; MID='#5E9FE0'; PALE='#C6DDF4'; PANEL='#EEF3F6'; LINE='#D9DEE3'; INK='#222222'; MUTED='#6B7C85'
FONT=a.font; FONTS={}; CHECKS=[]; BREAKER=budoux.load_default_japanese_parser()
def font(size,weight=400):
    k=(size,weight)
    if k not in FONTS:
        f=ImageFont.truetype(FONT,size)
        try:f.set_variation_by_axes([weight])
        except Exception:pass
        FONTS[k]=f
    return FONTS[k]
def esc(t):return html.escape(str(t),quote=True)
def clean(t):return str(t).replace('——','、').replace('—','〜').replace('–','〜').replace('―','〜')
def wrap(t,width,size=20,weight=400):
    f=font(size,weight); lines=[]
    for paragraph in clean(t).split('\n'):
        first=len(lines)
        toks=[]
        for phrase in BREAKER.parse(paragraph):
            if f.getlength(phrase)<=width:toks.append(phrase)
            else:toks.extend(re.findall(r'[A-Za-z0-9]+(?:[.,:/%％-][A-Za-z0-9]+)*|[一-龯々〆]+[ぁ-ん]*|[ァ-ヶー]+|.',phrase))
        line=''
        for token in toks:
            if line and f.getlength(line+token)>width:
                if token in '、。）」』】？！％' and len(line)>1:
                    lines.append(line[:-1]);line=line[-1]+token;continue
                if line[-1:] in '（「『【':token=line[-1]+token;line=line[:-1]
                lines.append(line);line=token
            else:line+=token
        if line:lines.append(line)
        if len(lines)>first+1 and 0<len(lines[-1])<=2:
            prev=BREAKER.parse(lines[-2]);tail=lines[-1]
            if len(prev)>1:lines[-2:]=[''.join(prev[:-1]),prev[-1]+tail]
    # Avoid an isolated final one or two characters.
    if len(lines)>1 and 0<len(lines[-1])<=2:
        prev=BREAKER.parse(lines[-2]);tail=lines[-1]
        if len(prev)>1:lines[-2:]=[''.join(prev[:-1]),prev[-1]+tail]
    return lines or ['']

class Canvas:
    def __init__(self,s):self.s=s;self.e=[];self.bounds=[];self.err=[]
    def rect(self,x,y,w,h,fill='none',stroke=None,dash=False,sw=1):
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+(' stroke-dasharray="8 6"' if dash else '')+'/>')
    def line(self,x1,y1,x2,y2,color=LINE,sw=1,dash=False):
        self.e.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"'+(' stroke-dasharray="8 6"' if dash else '')+'/>')
    def text(self,x,y,t,size=20,w=None,weight=400,color=INK,lh=None,maxh=None,link=None,ident=None):
        t=clean(t);lh=lh or round(size*1.5);ll=wrap(t,w,size,weight) if w else t.split('\n')
        h=size+(len(ll)-1)*lh
        if maxh is not None and h>maxh+1:self.err.append(f'{ident or t[:16]}: height {h}>{maxh}')
        width=max(font(size,weight).getlength(z) for z in ll)
        if x+width>1835 and ident!='page':self.err.append(f'right overflow {t[:25]}')
        if size<18:self.err.append('font under18')
        if any(len(z.strip()) in [1,2] for z in ll[1:]):self.err.append(f'isolated line {t[:24]}')
        attrs=f' x="{x}" y="{y+size}" font-size="{size}" font-weight="{weight}" fill="{color}"'
        if ident:attrs+=f' data-element="{esc(ident)}"'
        item=f'<text{attrs}>'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else lh}">{esc(z)}</tspan>' for i,z in enumerate(ll))+'</text>'
        if link:item=f'<a href="{esc(link)}"'+(' target="_blank" rel="noopener"' if not link.startswith('#') else '')+f'>{item}</a>'
        self.e.append(item);self.bounds.append(dict(id=ident or t[:20],x=x,y=y,w=width,h=h,size=size))
        return h
    def label(self,x,y,t,w=None):return self.text(x,y,t,20,w,700,BLUE,28)
    def table(self,headers,rows,widths,x=86,y=300,height=620,links=None,font_size=20):
        hh=58;rh=(height-hh)/max(1,len(rows));full=sum(widths)
        self.rect(x,y,full,hh,PANEL)
        for i,label in enumerate(headers):self.text(x+sum(widths[:i])+16,y+14,label,20,widths[i]-32,700,maxh=38)
        for j,row in enumerate(rows):
            yy=y+hh+j*rh;self.line(x,yy,x+full,yy)
            for i,v in enumerate(row):
                self.text(x+sum(widths[:i])+16,yy+16,v,font_size,widths[i]-32,700 if i==0 else 400,BLUE if i==0 else INK,30,rh-24,links.get((j,i)) if links else None,ident=f'row{j+1}-col{i+1}')
        self.line(x,y+height,x+full,y+height)
    def finish(self):
        for b in self.bounds:
            if b['y']+b['h']>1080:self.err.append('canvas overflow '+b['id'])
        CHECKS.append({'key':self.s['key'],'errors':self.err,'bounds':self.bounds})
        return '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-labelledby="title-'+self.s['key']+'" style="font-family:Noto Sans JP,sans-serif"><title id="title-'+self.s['key']+'">'+esc(self.s['head'])+'</title><rect width="1920" height="1080" fill="white"/>'+''.join(self.e)+'</svg>'

def short_note(s):
    n=s['note']
    if s['kind']=='case':
        if s['key'][0] in 'CM':
            n=n.split('掲載総事業費')[0].split('原資料時点')[0].strip()+' 事業費は年間運行費と異なる。現況未追跡。還元と次の確認は分析・提案。'
        elif s['key'][0]=='D':
            n=re.sub(r'^観測期間：.*?。','',n)
            n=n.split('資金経路は')[0].strip()+' 現況は各出典の時点。資金経路・期待価値は分析、次の確認は提案。'
        else:
            n=n.split('現在の運行')[0].strip()
            if len(n)>135:n=n.split('活動メニュー')[0].strip()
    return n
def sources(c,s):
    x=86;y=1040
    label='出所：'
    for k in s['sources']:
        if k in RAW:
            r=RAW[k];name=k
            link=r['追加出典URL'] if k in ['D21','D22'] and r['追加出典URL'] else r['出典URL']
            if s['kind']=='case':name=f"台帳「{r['sheet']}」{r['row']}行／{r['原資料位置']}"
            text=label+name;c.text(x,y,text,18,link=link,color=MUTED,ident='source');x+=font(18).getlength(text)+22;label=''
        else:
            name=k.replace('PDF','調査編').replace('OITA','大分交通構造PDF').replace('LVOS','LVOS大分.txt').replace('AUDIT','台帳再集計')
            text=label+name;c.text(x,y,text,18,color=MUTED,ident='source');x+=font(18).getlength(text)+22;label=''
        if x>1540:break
    c.text(1690,1040,f"{s['no']:03} / {len(SLIDES):03}",18,color=MUTED,ident='page')

def shell(c,s):
    c.text(86,58,DOC['title'] if s['kind']=='summary' else s['section'],28,color=BLUE,weight=700)
    c.text(86,111,s['head'],48,w=1748,weight=700,lh=58,maxh=60,ident='head')
    c.text(86,218,s['title'],24,w=1748,weight=700,lh=33,maxh=66,ident='figure-title')
    c.line(86,294,1834,294)

def render(s):
    c=Canvas(s);shell(c,s);b=s['body'];k=s['kind']
    if k=='summary':
        rows=[]
        for d in b['decisions']:
            ref=d['ref']
            for key in sorted(PAGE,key=len,reverse=True):ref=ref.replace(key,str(PAGE[key]))
            rows.append([f"{d['no']}  {d['label']}",d['decision'],d['condition'],ref+'頁'])
        c.table(['論点','求める決定','決定を支える条件','参照'],rows,[240,625,618,265],y=320,height=445)
        for i,(rid,txt) in enumerate(b['anchors']):
            xx=86+i*598;c.text(xx,810,txt,24,weight=700);c.text(xx,855,RAW[rid]['事例'],20,w=538,maxh=62,link='#'+rid)
    elif k=='scope':
        c.text(86,318,'掲載記録数（件）',24,weight=700)
        chartx=320;chartw=820
        for i,(name,n,period) in enumerate(b['counts']):
            yy=380+i*125;c.text(86,yy+5,name,24,weight=700);c.text(86,yy+42,period,18,color=MUTED)
            c.rect(chartx,yy,chartw*n/40,55,BLUE if i==0 else MID);c.text(chartx+chartw*n/40+18,yy+7,str(n),28,weight=700,color=BLUE)
        c.line(chartx,879,chartx+chartw,879)
        for tick in [0,10,20,30,40]:c.text(chartx+chartw*tick/40-8,890,str(tick),18,color=MUTED)
        c.line(1234,330,1234,934)
        c.text(1300,318,'費用情報の範囲（件）',24,weight=700)
        for i,(num,title,txt) in enumerate(b['limits']):
            yy=382+i*173;c.text(1300,yy,num,48,weight=700,color=BLUE);c.text(1440,yy+10,title,24,weight=700)
            c.text(1300,yy+72,txt,20,w=530,maxh=74)
    elif k=='returns':
        c.text(86,318,'還元の設計（提案）',24,weight=700)
        c.table(['還元先','戻したい価値','確かめること'],b['rows'],[160,480,410],y=372,height=557)
        c.text(1218,318,'実際に分かる金額（原資料時点）',24,weight=700)
        for i,(rid,num,txt) in enumerate(b['examples']):
            yy=395+i*276;c.text(1218,yy,rid+' '+RAW[rid]['地域'],20,color=MUTED,link='#'+rid)
            c.text(1218,yy+46,num,44,color=BLUE,weight=700)
            c.text(1218,yy+120,txt,24,w=605,lh=38,maxh=120)
    elif k=='menu_index':
        rows=[];links={}
        objectives=['生活の活動を守る','地元の商いへつなぐ','滞在と体験を広げる','家族・施設の送迎を支える','参加できる場をつくる','災害に備える','地域で挑戦する人を育てる','地域の運営を支える']
        for i,m in enumerate(b['menus']):
            rows.append([m['id'],m['name'],objectives[i],m['dealer_role']]);links[(i,1)]='#M'+m['id']
        c.table(['','活動メニュー','地域の目的','販売店の資産と仕事'],rows,[70,360,500,818],y=316,height=622,links=links)
    elif k=='menu':
        c.text(86,320,'販売店が地域と行うこと',24,weight=700)
        c.text(86,366,b['action'],28,w=800,weight=700,lh=43,maxh=90)
        c.label(86,478,'販売店の役割');c.text(86,514,b['dealer_role'],20,w=800,maxh=65)
        c.label(86,610,'継続する財源と測り方');c.text(86,649,b['funding'],20,w=800,maxh=64)
        c.text(86,725,'確認指標：'+b['metric'],20,w=800,maxh=65)
        c.text(86,818,'先行例（各資料時点）',24,weight=700)
        for i,ex in enumerate(b['examples']):
            yy=862+i*41;c.text(86,yy,ex['id']+'  '+ex['fact'],20,w=800,maxh=34,link='#'+ex['id'])
        c.text(972,320,'地元と販売店に戻す価値（応用仮説）',24,weight=700)
        rows=[['住民',b['resident_return']],['地元企業',b['local_business_return']],['販売店',b['dealer_return']],['地域',b['regional_return']]]
        c.table(['還元先','期待する変化'],rows,[156,706],x=972,y=376,height=442)
        c.label(972,862,'事前に決める負担');c.text(972,904,'活動費xx円、販売店の上限xx円、担当者xx。',20,w=860,maxh=35)
    elif k=='options':
        rows=[]
        for r in b['rows']:
            d=r['criteria'];rows.append([r['name'],r['logic'],d['販売店に戻る価値']+'\n'+d['地元の仕事・所得'],d['継続負担と費用']+'\n'+d['責任・人材依存'],d['広げる条件']])
        c.table(['参画方法','仕事の中心','自社・地元への還元','負担・責任','広げる条件'],rows,[195,365,438,438,312],y=310,height=630)
    elif k=='oita':
        c.table(['地域の条件','観測事実','活動の使い方（案）','現地で確かめること'],b['rows'],[238,506,504,500],y=330,height=590)
    elif k=='lvos':
        c.text(86,322,'地域に帰属する追加付加価値（試算の定義）',24,weight=700)
        positions=[86,697,1294];widths=[514,505,540]
        for i,t in enumerate(b['formula']):
            c.rect(positions[i],382,widths[i],118,stroke=BLUE,dash=True,sw=2);c.text(positions[i]+20,400,t,24,w=widths[i]-40,weight=700,maxh=65)
            c.text(positions[i]+20,455,'xx円' if i==0 else 'xx',24,color=BLUE,weight=700)
            if i<2:c.text(positions[i]+widths[i]+35,417,'×',36)
        c.table(['評価対象','測るもの','単位と未確定値','測定条件'],b['rows'],[190,536,340,682],y=552,height=387)
    elif k=='funding':
        c.table(['構造','負担する主体','運営を支えるもの','成立を確かめる条件','参照'],b['rows'],[265,322,470,452,239],y=310,height=637)
    elif k=='risk':
        c.text(86,321,'先行事例で生じた制約（原資料時点）',24,weight=700)
        for i,(rid,title,txt) in enumerate(b['evidence']):
            yy=382+i*181;c.text(86,yy,rid+'  '+title,24,w=815,weight=700,maxh=36,link='#'+rid)
            c.text(86,yy+51,txt,20,w=815,maxh=72);c.line(86,yy+145,901,yy+145)
        c.text(978,321,'判断を変える条件（提案）',24,weight=700)
        c.table(['判定','条件'],b['rules'],[182,674],x=978,y=379,height=430)
        c.label(978,857,'需要増・担い手不足・支払未達を別々に試す')
        c.text(978,900,'人気がある場合も供給力と許容負担を再判定する。',20,w=856,maxh=36)
    elif k=='case':
        r=b['raw'];period=r['観測期間'];c.text(86,265,'観測期間：'+period,18,w=1748,color=MUTED,maxh=25)
        c.text(86,325,'活動と確認された実績',24,weight=700)
        yy=376
        for i,txt in enumerate(b['facts']):
            h=c.text(86,yy,txt,20,w=815,maxh=66,ident=f'fact-{i+1}');yy+=max(57,h+18)
        c.text(86,586,'負担と資金の流れ（資料の記載）',24,weight=700)
        vals=[('負担者',b['payer']),('利用者負担',r['利用者負担'] or '記載なし'),('運営への還流',b['capture'])]
        for i,(lab,txt) in enumerate(vals):
            yy=632+i*82;c.label(86,yy,lab);c.text(257,yy,txt,20,w=644,maxh=63);c.line(86,yy+70,901,yy+70)
        cost=r['総事業費（千円）'];cost='xx 千円（記載なし）' if cost is None else f'{cost:,.0f} 千円'
        c.label(86,902,'掲載総事業費');c.text(335,896,cost,28,w=566,weight=700,color=BLUE,maxh=42)
        c.text(972,325,'地元と販売店への還元',24,weight=700)
        roles=[('住民','residents'),('地元企業','business'),('販売店','dealer'),('地域','region')]
        for i,(lab,key) in enumerate(roles):
            yy=379+i*83;c.label(972,yy,lab);c.text(1130,yy,b['returns'][key],20,w=704,maxh=65,ident='return-'+key);c.line(972,yy+72,1834,yy+72)
        c.label(972,739,'継続判断に足りない情報');c.text(972,779,b['gap'],20,w=862,maxh=67,ident='gap')
        c.label(972,858,'次に確かめること（提案）');c.text(972,900,b['action'],20,w=862,maxh=61,ident='next-action')
    elif k=='closing':
        rows=[]
        answers=['対象者xx／優先活動xx／実現したいことxx','選ぶ参画方法xx／地域側・自社の責任者xx','地元の便益xx／予算xx円／自社上限xx円','測定担当xx／判定値xx／次回会議日xx']
        for i,d in enumerate(b['decisions']):rows.append([str(d['no'])+' '+d['label'],d['decision'],answers[i]])
        c.table(['決定事項','会議で決める内容','記入・合意する条件'],rows,[240,680,828],y=315,height=365)
        c.text(86,721,'直近からの確認日程（提案）',24,weight=700)
        for i,(when,act,owner) in enumerate(b['schedule']):
            xx=86+i*596;c.rect(xx,767,550,143,stroke=BLUE,dash=True);c.text(xx+18,778,when,24,weight=700,color=BLUE)
            c.text(xx+18,820,act,20,w=514,maxh=60);c.text(xx+18,869,owner,18,w=514,maxh=26)
        c.text(86,923,'判断基準：'+b['gate'],18,w=1748,maxh=27)
    if s['discussion']:
        # Decision boxes only on the two decision pages.
        y=947 if k=='closing' else 936;c.rect(86,y,1748,42,PANEL);c.text(102,y+7,'論点',20,weight=700,color=BLUE)
        c.text(170,y+7,s['discussion'],20,w=1640,maxh=28)
    n=short_note(s)
    c.text(86,990 if k=='closing' else 980,n,18,w=1748,lh=25,maxh=49,ident='note')
    sources(c,s)
    return c.finish()

svgs=[render(s) for s in SLIDES]

# Embed a subset so the single HTML also works without a font network connection.
characters=''.join(re.findall(r'>([^<>]*)<',''.join(svgs)))+DOC['title']+DOC['subtitle']
ft=TTFont(FONT);opt=subset.Options();opt.flavor='woff';sub=subset.Subsetter(options=opt);sub.populate(text=characters);sub.subset(ft);ft.flavor='woff';buf=io.BytesIO();ft.save(buf)
font64=base64.b64encode(buf.getvalue()).decode()

sections=[]
for s,svg in zip(SLIDES,svgs):
    if s['kind']=='case':
        b=s['body'];r=b['raw'];details='<dl>'+''.join('<dt>'+esc(name)+'</dt><dd>'+esc(val)+'</dd>' for name,val in [('主体・担当',r['主体・担当']),('価値経路の分析',b['flow']),('確認担当の案',b['owner']),('次の判断基準',b['criterion']),('注記の全文',s['note'])])+'</dl>'
    else:details='<p>'+esc(s['note'])+'</p>'
    nav=f'<div class="page-tools"><a href="#'+s['key']+'">'+str(s['no']).zfill(3)+' '+esc(s['key'])+'</a><button class="enlarge" data-slide="'+s['key']+'">拡大する</button><details><summary>根拠・次の確認</summary>'+details+'</details></div>'
    sections.append(f'<article class="sheet" data-key="{s["key"]}" data-kind="{s["kind"]}"><div class="slide-viewport"><section id="{s["key"]}" class="slide" aria-label="{s["no"]} {esc(s["head"])}">{svg}</section></div>{nav}</article>')
index=[{'key':s['key'],'no':s['no'],'kind':s['kind'],'title':s['title'],'head':s['head'],'menu':s['body'].get('menu','') if isinstance(s['body'],dict) else ''} for s in SLIDES]
style='''
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:85px}body{margin:0;background:#E6EBEF;color:#222;font-family:"Noto Sans JP",sans-serif}button,input,select{font:inherit}a{color:#1976D2}button,a,input,select{touch-action:manipulation}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #1976D2;outline-offset:3px}button{cursor:pointer;background:white;border:1px solid #c2cbd2;padding:8px 13px;border-radius:2px;color:#222}header{position:sticky;top:0;z-index:10;background:white;border-bottom:1px solid #d9dee3;padding:12px 24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;min-height:70px}header strong{font-size:17px;margin-right:auto}header a{font-size:15px}#counter{font-size:14px;color:#6B7C85}#jump{max-width:220px;font-size:15px;padding:8px}main{padding:28px 20px 60px;max-width:1970px;margin:auto}.sheet{margin:0 auto 38px;max-width:1920px}.slide-viewport{width:100%;aspect-ratio:16/9;background:white;box-shadow:0 6px 24px #14263712;overflow:hidden}.slide{width:1920px;height:1080px;transform-origin:top left;position:relative;background:white}.slide svg{display:block;width:1920px;height:1080px}.slide a:hover text{fill:#145ca4;text-decoration:underline}.page-tools{display:flex;gap:14px;align-items:flex-start;padding:12px 0;font-size:14px;color:#6B7C85}.page-tools>a{padding:9px 0;min-width:75px}.page-tools details{background:#F4F7F9;flex:1;max-width:1400px;padding:9px 14px;font-size:15px}.page-tools summary{cursor:pointer}.page-tools dt{font-weight:700;color:#222;margin-top:12px}.page-tools dd{margin:5px 0 15px;line-height:1.9;color:#222}dialog{border:0;padding:0;width:min(1000px,95vw);max-height:85vh;box-shadow:0 20px 60px #0004}dialog::backdrop{background:#14263788}.dialog-head{display:flex;align-items:center;justify-content:space-between;padding:20px;border-bottom:1px solid #d9dee3}#search{margin:20px;width:calc(100% - 40px);padding:14px;border:1px solid #c2cbd2;font-size:18px}#results{padding:0 20px 20px;max-height:58vh;overflow:auto}#results a{display:block;text-decoration:none;padding:16px 4px;border-bottom:1px solid #d9dee3;color:#222;font-size:16px}#results small{display:block;color:#6B7C85;margin-bottom:5px}.sheet[hidden]{display:none}body.focus .sheet{display:none}body.focus .sheet.current{display:block}body.focus main{max-width:none}body.focus .page-tools{display:none}body.zoom main{max-width:none}body.zoom .slide-viewport{overflow:auto;aspect-ratio:auto;height:min(82vh,1080px)}body.zoom .slide{transform:none!important}body.zoom .sheet{max-width:none}#mobile-hint{display:none}footer{font-size:14px;color:#6B7C85;padding:20px;text-align:center}@media(max-width:750px){header{padding:10px 12px;gap:8px}header strong{width:100%;font-size:16px}header a{font-size:14px}#jump{max-width:165px}main{padding:15px 8px 30px}.sheet{margin-bottom:16px}.page-tools{flex-wrap:wrap;font-size:13px}.page-tools details{flex-basis:100%}#mobile-hint{display:block;padding:12px 16px;background:#fff;color:#6B7C85;font-size:14px}#counter{display:none}}@media print{@page{size:508mm 285.75mm;margin:0}body{background:white}header,.page-tools,footer,#mobile-hint,dialog{display:none!important}main{padding:0;max-width:none;margin:0}.sheet,body.focus .sheet{display:block!important;margin:0;width:1920px;break-after:page}.slide-viewport{width:1920px;height:1080px;box-shadow:none;overflow:visible}.slide{transform:none!important}.sheet:last-child{break-after:auto}}
'''
js='''
const DATA=__INDEX__;let current=0;const sheets=[...document.querySelectorAll('.sheet')];const jump=document.querySelector('#jump');
function fit(){document.querySelectorAll('.slide-viewport').forEach(v=>{v.querySelector('.slide').style.transform=`scale(${v.clientWidth/1920})`});}
function show(n,scroll=true){current=Math.max(0,Math.min(DATA.length-1,n));sheets.forEach((s,i)=>s.classList.toggle('current',i===current));jump.value=DATA[current].key;document.querySelector('#counter').textContent=`${current+1} / ${DATA.length}`;history.replaceState(null,'','#'+DATA[current].key);if(scroll&&!document.body.classList.contains('focus'))sheets[current].scrollIntoView({block:'start'});fit();}
DATA.forEach((d,i)=>{const o=document.createElement('option');o.value=d.key;o.textContent=String(d.no).padStart(3,'0')+' '+(d.kind==='case'?d.title:d.head);jump.append(o)});jump.onchange=()=>show(DATA.findIndex(d=>d.key===jump.value));
window.addEventListener('resize',fit);document.fonts.ready.then(fit);window.addEventListener('hashchange',()=>{const i=DATA.findIndex(d=>d.key===location.hash.slice(1));if(i>=0)show(i)});
document.querySelector('#prev').onclick=()=>show(current-1);document.querySelector('#next').onclick=()=>show(current+1);document.querySelector('#focus').onclick=()=>{document.body.classList.toggle('focus');document.querySelector('#focus').textContent=document.body.classList.contains('focus')?'全ページ表示':'会議表示';show(current,false);window.scrollTo(0,0)};
document.querySelector('#zoom').onclick=()=>{document.body.classList.toggle('zoom');document.querySelector('#zoom').textContent=document.body.classList.contains('zoom')?'画面に合わせる':'原寸で読む';fit()};
document.querySelectorAll('.enlarge').forEach(b=>b.onclick=()=>{document.body.classList.add('zoom');document.querySelector('#zoom').textContent='画面に合わせる';show(DATA.findIndex(d=>d.key===b.dataset.slide))});
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(a){const i=DATA.findIndex(d=>d.key===a.getAttribute('href').slice(1));if(i>=0){e.preventDefault();show(i);}}});
document.addEventListener('keydown',e=>{if(/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||document.querySelector('dialog[open]'))return;if(e.key==='ArrowRight'||e.key==='PageDown'){e.preventDefault();show(current+1)}if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();show(current-1)}if(e.key==='Escape'&&document.body.classList.contains('zoom')){document.body.classList.remove('zoom');fit()}});
const dialog=document.querySelector('#catalog');function search(){const q=document.querySelector('#search').value.trim().toLowerCase();const found=DATA.filter(d=>(d.key+' '+d.title+' '+d.head+' '+d.menu).toLowerCase().includes(q));const r=document.querySelector('#results');r.replaceChildren();for(const d of found){const a=document.createElement('a');a.href='#'+d.key;const sm=document.createElement('small');sm.textContent=String(d.no).padStart(3,'0')+'  '+d.key+'  '+d.title;a.append(sm,document.createTextNode(d.head));a.onclick=e=>{e.preventDefault();dialog.close();show(d.no-1)};r.append(a)}if(!found.length)r.textContent='一致するページがありません。地域名や事例IDで検索してください。';}
document.querySelector('#open-catalog').onclick=()=>{dialog.showModal();search();document.querySelector('#search').focus()};document.querySelector('#close-catalog').onclick=()=>dialog.close();document.querySelector('#search').addEventListener('input',search);
const io=new IntersectionObserver(es=>{if(document.body.classList.contains('focus'))return;for(const e of es)if(e.isIntersecting){current=sheets.indexOf(e.target);jump.value=DATA[current].key;document.querySelector('#counter').textContent=`${current+1} / ${DATA.length}`;}},{threshold:.55});sheets.forEach(s=>io.observe(s));
fit();const initial=DATA.findIndex(d=>d.key===location.hash.slice(1));show(initial<0?0:initial,false);if(initial>=0)requestAnimationFrame(()=>sheets[initial].scrollIntoView());
window.catalogQA={count:DATA.length,keys:DATA.map(d=>d.key),ready:true};
'''.replace('__INDEX__',json.dumps(index,ensure_ascii=False).replace('</','<\\/'))
page='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+esc(DOC['title'])+'｜町いちばん活動カタログ</title><meta name="description" content="販売店と地元に何が戻るか。8つの町いちばん活動メニューと88掲載記録を、役割・還元・負担・継続条件から比較する経営会議用カタログ。"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap"><style>@font-face{font-family:"Noto Sans JP";src:url(data:font/woff;base64,'+font64+') format("woff");font-weight:100 900;font-display:swap}'+style+'</style></head><body><header><strong>町いちばん活動カタログ</strong><button id="open-catalog">目次・事例検索</button><button id="prev" aria-label="前のページ">前へ</button><select id="jump" aria-label="ページを選択"></select><button id="next" aria-label="次のページ">次へ</button><span id="counter"></span><button id="focus">会議表示</button><button id="zoom">原寸で読む</button><a href="blueprint.html">A 設計図</a></header><div id="mobile-hint">各ページの「拡大する」で文字を原寸表示できます。左右に移動してご覧ください。</div><main>'+''.join(sections)+'</main><footer>2026年9月27日作成。資料時点と現況、確認された実績と応用仮説を区別しています。</footer><dialog id="catalog"><div class="dialog-head"><strong>活動・地域・事例を選ぶ</strong><button id="close-catalog">閉じる</button></div><input id="search" type="search" aria-label="事例を検索" placeholder="暮らしの足、別府、D05 など"><div id="results"></div></dialog><script>'+js+'</script></body></html>'
(BASE/'catalog.html').write_text(page)

# Blueprint HTML is the separate A deliverable, including the full evidence map.
md=(BASE/'blueprint.md').read_text()
try:
    import markdown
    article=markdown.markdown(md,extensions=['tables','fenced_code','toc'])
except ImportError:
    article='<pre style="white-space:pre-wrap">'+esc(md)+'</pre>'
bluehtml='<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>A 設計図｜町いちばん活動</title><style>body{font-family:system-ui,sans-serif;max-width:1280px;margin:40px auto;padding:0 24px;line-height:1.8;color:#222}h1,h2,h3,a{color:#1976D2}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #D9DEE3;padding:12px;vertical-align:top;text-align:left}th{background:#EEF3F6}pre{white-space:pre-wrap;background:#EEF3F6;padding:20px;overflow:auto;font-size:14px}h3{border-top:2px solid #1976D2;padding-top:24px;margin-top:50px}a{overflow-wrap:anywhere}</style><p><a href="catalog.html">106枚のHTMLスライドを開く</a>　<a href="blueprint.md">設計図のMarkdown</a></p>'+article+'</html>'
(BASE/'blueprint.html').write_text(bluehtml)
qa=Path(a.qa) if a.qa else BASE/'.qa';qa.mkdir(parents=True,exist_ok=True)
(qa/'layout-checks.json').write_text(json.dumps(CHECKS,ensure_ascii=False,indent=2))
for s,svg in zip(SLIDES,svgs):(qa/(s['key']+'.svg')).write_text(svg)
(qa/'deck.js').write_text(js)
print(json.dumps({'slides':len(SLIDES),'html_bytes':len(page.encode()),'font_bytes':len(buf.getvalue()),'layout_errors':[{'key':r['key'],'errors':r['errors']} for r in CHECKS if r['errors']]},ensure_ascii=False,indent=2))
