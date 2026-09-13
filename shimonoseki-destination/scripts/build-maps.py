from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1] / 'assets'
BLUE='#82D6F7'; BLACK='#111111'; PINK='#82D6F7'; LEMON='#F7F4EE'; CORAL='#82D6F7'; LIME='#F7F4EE'; PAPER='#F7F4EE'

class SVG:
    def __init__(self,w,h,title,desc):
        self.w=w; self.h=h
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><g font-family="Noto Sans CJK JP,Noto Sans JP,Hiragino Kaku Gothic ProN,Meiryo,sans-serif" fill="{BLACK}">']
        self.rect(0,0,w,h,PAPER,0)
    def rect(self,x,y,w,h,fill='white',sw=2,stroke=BLACK,rx=0,dash=''):
        if fill=='white': fill=PAPER
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def path(self,d,color=BLACK,width=4,dash='',fill='none'):
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def poly(self,pts,fill,sw=2):
        if fill=='white': fill=PAPER
        self.parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{BLACK}" stroke-width="{sw}" stroke-linejoin="round"/>')
    def circle(self,x,y,r=11,fill='white',stroke=BLACK,sw=3):
        if fill=='white': fill=PAPER
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def text(self,x,y,txt,size=26,weight=700,fill=BLACK,anchor='start'):
        if fill=='white': fill=BLACK
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(txt)}</text>')
    def label(self,x,y,text,color='white',size=23,pad=14):
        # Japanese width is one em; Latin labels use a compact estimate.
        w=sum(size*(.6 if ord(c)<128 else 1) for c in text)+2*pad
        self.rect(x,y-size,w,size+17,color,0,rx=2)
        self.text(x+pad,y,text,size)
    def save(self,name):
        (OUT/name).write_text('\n'.join(self.parts)+ '\n</g></svg>\n')

floors=[('5F','暮らす・働く','医療・学習・仕事の候補',LIME),('4F','体験する・学ぶ','海峡の航海ゲーム・親子の体験',CORAL),('3F','好きに出会う','IP展示・参加型劇場の候補',PINK),('2F','日本を持ち帰る','日本ブランド × 地域のつくり手',BLUE),('1F','食べる・旅立つ','食の拠点・夜の食事・観光案内',LEMON),('B1','日常を支える','地元食材・日々の買い物',BLUE)]

def building(mobile=False):
    w,h=(640,990) if mobile else (1180,820)
    s=SVG(w,h,'建物の立体構成イメージ・フロア機能の配置案','大丸下関店の営業終了後を見据えた独自構想。B1は日常の買い物、1Fは食と旅の入口、2Fは日本ブランド、3FはIP、4Fは体験、5Fは暮らしと仕事の候補。実測図・設計図ではなく、対象階と動線は未確定。')
    s.text(24 if mobile else 40,38,'SPACE / 機能を積み重ねる',25 if mobile else 22)
    if not mobile: s.text(1135,38,'配置案・寸法なし',19,500,anchor='end')
    # Dashed vertical alignment shows an exploded stack, not a staircase or escape route.
    if mobile:
        s.path('M130 84 V850 M330 129 V895', BLACK,2,'5 8')
    else:
        s.path('M260 82 V690 M590 134 V742 M410 195 V803',BLACK,2,'5 8')
    for i,(floor,title,detail,color) in enumerate(floors):
        y=(86+i*136) if mobile else (78+i*113)
        if mobile:
            a,b,c,d=(130,y),(330,y+45),(210,y+93),(10,y+48)
            thick=12; labelx=365; labely=y+22; title_size=28
            plane=(1,.225,-1,.4,130,y); pw,ph=200,120
        else:
            a,b,c,d=(260,y),(590,y+52.8),(410,y+108.6),(80,y+55.8)
            thick=13; labelx=680; labely=y+33; title_size=31
            plane=(1,.16,-1,.31,260,y); pw,ph=330,180
        points=lambda arr:' '.join(f'{x},{v}' for x,v in arr)
        s.poly(points([d,c,(c[0],c[1]+thick),(d[0],d[1]+thick)]),color)
        s.poly(points([b,c,(c[0],c[1]+thick),(b[0],b[1]+thick)]),'white')
        s.poly(points([a,b,c,d]),color)
        s.parts.append('<g transform="matrix('+ ' '.join(map(str,plane)) + ')">')
        # Color zones suggest activity areas; they are not a survey of the actual property.
        s.rect(15,14,pw*.42,ph*.37,'white',1.7)
        s.rect(pw*.54,14,pw*.39,ph*.37,'white',1.7)
        s.rect(15,ph*.56,pw*.60,ph*.33,'white',1.7)
        s.rect(pw*.73,ph*.55,pw*.20,ph*.34,BLACK,1.7)
        # Tables / flexible islands give spatial legibility without decorative 3D effects.
        if i in (0,3,5):
            for xx in [26,54,82]: s.rect(xx,ph*.63,16,ph*.16,color,1)
        elif i in (1,2):
            for xx in [28,57,86]: s.circle(xx,ph*.73,7,color,BLACK,1)
        else:
            s.rect(26,ph*.63,pw*.43,ph*.14,color,1)
        s.parts.append('</g>')
        s.path(f'M{b[0]} {b[1]+4} H{labelx-20}',BLACK,1.8)
        s.rect(labelx,labely-24,68 if mobile else 78,33,color,1.5)
        s.text(labelx+9,labely+1,floor+' 案',22 if mobile else 24)
        mobile_titles=['暮らし・仕事','体験・学び','IP・カルチャー','日本ブランド','食・観光案内','日常の買い物']
        s.text(labelx,labely+43,mobile_titles[i] if mobile else title,30 if mobile else title_size,900)
        if not mobile: s.text(labelx,labely+76,detail,21,500)
    if mobile:
        s.rect(16,922,608,50,PAPER,1)
        s.text(320,957,'食・観光を入口に、日常の利用を重ねる。',24,700,'white','middle')
    else:
        s.rect(650,759,480,41,PAPER,1)
        s.text(675,787,'食・観光を入口に、日常の利用を重ねる。',21,700,'white')
    s.save('map-building'+('-mobile' if mobile else '')+'.svg')

def local(mobile=False):
    desc='下関駅前と、海響館・唐戸市場・赤間神宮・城下町長府・新下関駅をつなぐ模式図。下関駅から海沿いの各地へ既存バス、新下関駅から下関駅へJR、新下関駅から城下町長府へ既存バス。水色の破線はこれらを周回する未運行の企画案。方位、距離、道路形状は示さない。'
    s=SVG(640 if mobile else 1180,1160 if mobile else 820,'下関市内のアクセシビリティ',desc)
    if mobile:
        # The coast runs down the right of a legible, vertical city circuit.
        s.path('M640 220 L585 340 L585 650 L455 760 L455 1160 H640 Z',BLUE,0,fill=BLUE)
        s.text(26,39,'CITY / 下関市内をひとつの旅に',25)
        s.path('M102 145 V928',BLACK,10)
        s.path('M102 145 V928',PAPER,4)
        s.path('M102 145 H470 V273',BLACK,5)
        s.path('M470 350 V425 L370 548 L310 700 L225 924',BLACK,5)
        s.path('M370 557 L411 702 L320 812',BLACK,4,'2 12')
        s.path('M206 925 L284 685 L343 534 L439 419 V187 H147 V840 Z',BLACK,11,'12 14')
        s.path('M206 925 L284 685 L343 534 L439 419 V187 H147 V840 Z',PINK,7,'12 14')
        s.label(177,409,'周回便',PINK,27)
        s.text(192,445,'企画案',25)
        s.label(17,416,'JR',PAPER,28)
        s.label(248,222,'路線バス',PAPER,28)
        s.label(393,391,'路線バス',PAPER,26)
        s.label(425,727,'徒歩等',PAPER,23)
        s.circle(102,145); s.circle(470,301); s.circle(370,548); s.circle(310,700); s.circle(225,866)
        s.rect(35,65,330,114,'white',2)
        s.text(54,102,'新幹線の入口',24,600)
        s.text(54,148,'新下関駅',38,900)
        s.rect(276,254,335,114,LIME,2)
        s.text(296,297,'城下町長府',37,900)
        s.text(296,341,'武家屋敷・土塀の町並み',24,500)
        s.rect(349,455,265,81,'white',2)
        s.text(369,505,'赤間神宮',36,900)
        s.rect(277,584,295,83,LEMON,2)
        s.text(299,638,'唐戸市場',38,900)
        s.rect(165,750,264,83,'white',2)
        s.text(185,804,'海響館',38,900)
        s.rect(32,904,478,129,LEMON,2.5)
        s.text(52,943,'下関駅前 / 構想拠点',35,900)
        s.text(52,982,'大丸下関店の営業終了後を想定',23,500)
        s.text(52,1015,'シーモール・駐車場と一体利用を検討',22,500)
        s.text(476,1080,'関門海峡',28,900,'white')
        s.text(28,1124,'接続を整理した模式図・縮尺なし',24,500)
    else:
        s.path('M1180 298 L1100 362 L1050 435 L882 475 L830 557 L670 628 L585 708 L510 820 H1180 Z',BLUE,0,fill=BLUE)
        s.text(40,39,'CITY / 下関市内をひとつの旅に',22)
        s.text(1138,39,'接続を整理した模式図・縮尺なし',19,500,anchor='end')
        s.path('M225 148 V676',BLACK,10)
        s.path('M225 148 V676',PAPER,4)
        s.path('M225 148 H950 V226',BLACK,5)
        s.path('M950 226 V313 L798 400 L643 497 L460 580 L280 673',BLACK,5)
        s.path('M807 411 L807 527 L649 585 L480 660',BLACK,4,'2 12')
        s.path('M280 675 L442 558 L625 475 L780 378 L923 291 V177 H190 V575 Z',BLACK,11,'12 14')
        s.path('M280 675 L442 558 L625 475 L780 378 L923 291 V177 H190 V575 Z',PINK,7,'12 14')
        s.label(35,418,'周回便',PINK,27)
        s.text(49,455,'企画案',24,700)
        s.label(247,365,'JR 山陽本線',PAPER,24)
        s.label(556,134,'既存の路線バス',PAPER,25)
        s.label(493,429,'既存の路線バス',PAPER,25)
        s.label(865,593,'徒歩などで回遊',PAPER,22)
        for x,y in [(225,148),(950,226),(798,400),(643,497),(460,580),(280,673)]: s.circle(x,y)
        s.rect(82,82,350,127,'white',2)
        s.text(107,121,'新幹線の入口',22,600)
        s.text(106,173,'新下関駅',41,900)
        s.rect(764,216,375,112,LIME,2)
        s.text(790,262,'城下町長府',37,900)
        s.text(790,300,'武家屋敷・土塀の町並み',23,500)
        s.rect(803,347,256,83,'white',2)
        s.text(826,400,'赤間神宮',37,900)
        s.rect(642,473,255,88,LEMON,2)
        s.text(665,529,'唐戸市場',40,900)
        s.rect(389,583,235,65,'white',2)
        s.text(414,631,'海響館',39,900)
        s.rect(45,658,440,119,LEMON,2.5)
        s.text(67,703,'下関駅前 / 構想拠点',37,900)
        s.text(67,738,'大丸下関店の営業終了後を想定',21,500)
        s.text(67,764,'シーモール・駐車場と一体利用を検討',20,500)
        s.text(812,696,'関門海峡',42,900,'white')
        s.text(814,730,'KANMON STRAIT',22,700,'white')
    s.save('map-city'+('-mobile' if mobile else '')+'.svg')

def regional(mobile=False):
    desc='関門を一体で巡る交通接続の模式図。新下関駅と下関駅はJR山陽本線、下関駅と唐戸は既存バス、唐戸港と門司港は既存の関門連絡船。下関駅から海峡を越えて門司駅・小倉駅へJR在来線、門司駅から門司港駅へJR。途中駅やバス停は省略。宿泊や夜の帰路の一体案内は未合意の構想。'
    s=SVG(640 if mobile else 1180,1090 if mobile else 820,'関門広域のアクセシビリティ',desc)
    if mobile:
        s.rect(0,403,640,224,BLUE,0)
        s.text(23,37,'REGION / 海峡を越えて、滞在する',24)
        s.path('M130 147 V720 H85 V835',BLACK,10)
        s.path('M130 147 V720 H85 V835',PAPER,4)
        s.path('M130 720 H500 V630',BLACK,10)
        s.path('M130 720 H500 V630',PAPER,4)
        s.path('M130 274 H496 V348',BLACK,5)
        s.path('M498 359 V630',BLACK,4,'10 9')
        s.rect(34,68,313,97,'white',2)
        s.text(54,101,'新幹線の入口',22,500)
        s.text(54,144,'新下関駅',36,900)
        s.label(149,213,'JR',PAPER,26)
        s.rect(25,249,305,131,LEMON,2.5)
        s.text(45,288,'下関駅前',36,900)
        s.text(45,325,'大丸営業終了後の構想拠点',21,500)
        s.text(45,357,'夜の食と文化・宿泊連携案',22,500)
        s.label(345,249,'路線バス',PAPER,24)
        s.rect(407,297,208,91,'white',2)
        s.text(427,333,'唐戸',34,900)
        s.text(427,369,'市場・港',25,500)
        s.text(184,468,'関門海峡',41,900,'white')
        s.label(161,552,'JR 在来線','white',26)
        s.label(351,594,'関門連絡船','white',26)
        s.circle(130,720);s.circle(500,720);s.circle(85,835)
        s.rect(362,622,254,80,'white',2)
        s.text(380,658,'門司港',33,900)
        s.text(380,688,'門司港駅',23,500)
        s.text(159,674,'門司駅',32,900)
        s.text(159,703,'門司港方面へ接続',20,500)
        s.label(255,762,'JR 在来線',PAPER,25)
        s.rect(32,821,276,82,'white',2)
        s.text(52,872,'小倉駅',38,900)
        s.text(345,853,'北九州市',32,900)
        s.text(345,885,'門司港・小倉にも泊まる',20,500)
        s.rect(23,937,594,115,'white',3,PINK,dash='11 7')
        s.text(44,975,'連携案 / 宿へ戻るまでをひとつに',26,900)
        s.text(44,1010,'下関・門司港・小倉の宿、荷物、夜の帰路。',22,500)
        s.text(44,1038,'深夜の船・バス・鉄道の運行は示しません。',22,500)
    else:
        s.rect(0,331,1180,260,BLUE,0)
        s.text(40,38,'REGION / 海峡を越えて、滞在する',22)
        s.text(1138,38,'交通の接続図・縮尺なし・途中駅を省略',19,500,anchor='end')
        s.path('M252 136 V430 L470 619 H984',BLACK,10)
        s.path('M252 136 V430 L470 619 H984',PAPER,4)
        s.path('M470 619 H186 V686',BLACK,10)
        s.path('M470 619 H186 V686',PAPER,4)
        s.path('M252 258 H978 V282',BLACK,5)
        s.path('M978 295 V591',BLACK,4,'10 9')
        s.rect(91,68,334,99,'white',2)
        s.text(115,102,'新幹線の入口',21,500)
        s.text(115,147,'新下関駅',39,900)
        s.label(274,209,'JR 山陽本線',PAPER,24)
        s.rect(56,229,455,106,LEMON,2.5)
        s.text(80,274,'下関駅前 / 構想拠点',38,900)
        s.text(80,313,'夜の食と文化を、関門に泊まる理由に。',22,500)
        s.label(594,244,'既存の路線バス',PAPER,25)
        s.rect(864,211,266,121,'white',2)
        s.text(887,257,'唐戸',39,900)
        s.text(887,299,'市場・海響館・港',25,500)
        s.text(590,436,'関門海峡',52,900,'white','middle')
        s.text(590,473,'KANMON STRAIT',24,700,'white','middle')
        s.label(145,504,'JR 在来線','white',25)
        s.label(785,553,'既存の関門連絡船','white',24)
        for x,y in [(470,619),(186,686),(978,619)]: s.circle(x,y)
        s.rect(63,664,279,100,'white',2)
        s.text(87,707,'小倉駅',39,900)
        s.text(87,744,'新幹線・街歩き・宿泊',21,500)
        s.text(443,675,'門司駅',34,900)
        s.text(443,708,'門司港方面へ接続',21,500)
        s.label(632,611,'JR 在来線',PAPER,23)
        s.rect(811,596,318,108,'white',2)
        s.text(834,641,'門司港・門司港駅',32,900)
        s.text(834,680,'街歩き・夜景・宿泊',23,500)
        s.rect(390,748,740,48,'white',3,PINK,dash='11 7')
        s.text(410,780,'連携案 / 下関・門司港・小倉の宿、荷物、夜の帰路を一体案内',21,700)
    s.save('map-kanmon'+('-mobile' if mobile else '')+'.svg')

for m in (False,True):
    building(m);local(m);regional(m)
print('Created 6 responsive SVG maps')
