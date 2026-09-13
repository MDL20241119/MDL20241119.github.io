"""Generate self-contained illustrated concept SVGs from GSI coastline data.
Connections and floor uses are proposals, not navigation or construction plans.
"""
from pathlib import Path
from html import escape
import base64,json,math,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets'
GEO=json.loads((OUT/'kanmon-geography.json').read_text())
PAPER='#F7F4EE';INK='#111111';SKY='#82D6F7'
ART=base64.b64encode((OUT/'map-landmarks-sheet.webp').read_bytes()).decode()
PLAY=base64.b64encode((OUT/'after-dark-play-sheet.webp').read_bytes()).decode()
POI={'station':(130.923021,33.949127),'shin':(130.948040,34.006175),'sumiyoshi':(130.956533,33.999639),'chofu':(130.981947,33.997543),'aquarium':(130.942361,33.954619),'market':(130.94585,33.95635),'akama':(130.9491,33.9595),'karato':(130.9443,33.95525),'mojiko':(130.962181,33.942559),'moji':(130.933664,33.904189),'kokura':(130.882638,33.888551)}
def merc(lon,lat):return ((lon+180)/360*4096,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*4096)
class SVG:
 def __init__(self,w,h,title,desc):
  self.clipcount=0;self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><defs><image id="landmarks" width="1254" height="1254" xlink:href="data:image/webp;base64,{ART}"/><image id="play" width="1672" height="941" xlink:href="data:image/webp;base64,{PLAY}"/></defs><g font-family="Noto Sans CJK JP,Noto Sans JP,Meiryo,sans-serif" fill="{INK}">'];self.rect(0,0,w,h)
 def rect(self,x,y,w,h,fill=PAPER,sw=0,rx=0,dash=''):self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{INK}" stroke-width="{sw}" stroke-dasharray="{dash}"/>')
 def path(self,d,color=INK,width=3,dash='',fill='none'):self.p.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash}"/>')
 def text(self,x,y,t,size=25,weight=500,anchor='start',halo=False):
  ha=f' paint-order="stroke" stroke="{PAPER}" stroke-width="9" stroke-linejoin="round"' if halo else ''
  self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{ha}>{escape(t)}</text>')
 def circle(self,x,y,r=5):self.p.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PAPER}" stroke="{INK}" stroke-width="2.5"/>')
 def icon(self,n,x,y,size):
  self.clipcount+=1;self.p.append(f'<defs><clipPath id="art{self.clipcount}"><rect x="{x}" y="{y}" width="{size}" height="{size}"/></clipPath></defs><g clip-path="url(#art{self.clipcount})">');self.p.append(f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="{n%3*418} {n//3*418} 418 418"><use xlink:href="#landmarks"/></svg></g>')
 def vignette(self,n,x,y,w,h):
  self.clipcount+=1;self.p.append(f'<defs><clipPath id="art{self.clipcount}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs><g clip-path="url(#art{self.clipcount})">');self.p.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" viewBox="{n%2*836} {n//2*470.5} 836 470.5"><use xlink:href="#play"/></svg></g>')
 def save(self,name):
  data='\n'.join(self.p)+'\n</g></svg>\n'
  for ident in ['play','landmarks']:
   if '#'+ident not in data:data=re.sub(r'<image id="'+ident+r'"[^>]*/>','',data)
  (OUT/name).write_text(data)
class Map:
 def __init__(self,s,bbox,rect,ident,rail=False):
  self.s=s;self.x,self.y,self.w,self.h=rect;left,bottom=merc(bbox[0],bbox[1]);right,top=merc(bbox[2],bbox[3]);self.scale=min(self.w/(right-left),self.h/(bottom-top));self.left=left;self.top=top;self.ox=self.x+(self.w-(right-left)*self.scale)/2;self.oy=self.y+(self.h-(bottom-top)*self.scale)/2
  s.p.append(f'<defs><clipPath id="{ident}"><rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" rx="8"/></clipPath></defs><g clip-path="url(#{ident})">')
  for f in GEO['water']:
   parts=[]
   for ring in f['geometry']:
    pts=[self.xy(*v) for v in ring]
    if not self.visible(pts):continue
    parts.append('M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)+' Z')
   if parts:s.p.append(f'<path d="{" ".join(parts)}" fill="{SKY}" fill-rule="evenodd"/>')
  if rail:
   for f in GEO['rail']:
    for line in f['geometry']:
     pts=[self.xy(*v) for v in line]
     if len(pts)<2 or not self.visible(pts):continue
     d='M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in pts);s.path(d,INK,3.3);s.path(d,PAPER,1.1)
  s.p.append('</g>')
 def visible(self,pts):return pts and not(max(p[0] for p in pts)<self.x or min(p[0] for p in pts)>self.x+self.w or max(p[1] for p in pts)<self.y or min(p[1] for p in pts)>self.y+self.h)
 def xy(self,x,y):return self.ox+(x-self.left)*self.scale,self.oy+(y-self.top)*self.scale
 def point(self,key):return self.xy(*merc(*POI[key]))
 def pointll(self,lon,lat):return self.xy(*merc(lon,lat))
 def route(self,coords,kind='bus'):
  pts=[self.point(v) if isinstance(v,str) else self.pointll(*v) for v in coords];d='M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)
  if kind=='proposal':self.s.path(d,INK,9,'13 12');self.s.path(d,SKY,5,'13 12')
  elif kind=='ferry':self.s.path(d,INK,4,'3 9')
  elif kind=='walk':self.s.path(d,INK,2,'2 6')
  else:self.s.path(d,INK,3.5)
 def landmark(self,key,n,label,dx=0,dy=-80,size=90,labelsize=25,sub=None):
  x,y=self.point(key);cx=x+dx;cy=y+dy;self.s.path(f'M{x:.1f},{y:.1f} L{cx:.1f},{cy+size*.65:.1f}',INK,1.4);self.s.icon(n,cx-size/2,cy,size);self.s.circle(x,y);self.s.text(cx,cy+size+19,label,labelsize,700,'middle',True)
  if sub:self.s.text(cx,cy+size+46,sub,labelsize-6,400,'middle',True)
def north(s,x,y):s.text(x,y,'N',19,700,'middle');s.path(f'M{x},{y+12} v35 m-8,-24 8,-11 8,11',INK,2)
def credit(s,y):s.text(25,y,'国土地理院ベクトルタイル提供実験を加工 / 北が上',16,400);s.text(25,y+26,'海岸線をもとに、施設位置と接続を簡略化した構想図。',16,400)
def city(mobile=False):
 w,h=(680,1300) if mobile else (1180,1000);s=SVG(w,h,'下関市内の周回イメージ','国土地理院の海岸線を土台とする市内地図。下関駅前、海響館、唐戸市場、赤間神宮、城下町長府、新下関駅、住吉神社。水色の破線は未運行の周回案。');s.text(25,43,'02 / まちを、ぐるっと。',32,700);s.text(25,77,'食・海・歴史をつなぐ CITY LOOP',20)
 rect,bbox=((15,100,650,720),(130.896,33.939,131.009,34.026)) if mobile else ((20,110,750,735),(130.892,33.937,131.012,34.027));m=Map(s,bbox,rect,'city-water',True)
 m.route(['station',(130.932,33.953),(130.939,33.954),'karato','akama',(130.971,33.973),'chofu']);m.route(['shin',(130.959,34.010),(130.981,34.008),'chofu'])
 m.route(['station',(130.918,33.963),(130.923,33.988),(130.937,34.013),'shin',(130.969,34.016),(130.990,34.009),'chofu',(130.975,33.976),'akama','karato',(130.936,33.951),'station'],'proposal')
 if mobile:
  m.landmark('shin',5,'新下関駅',-53,-120,102,29,'新幹線から');m.landmark('chofu',4,'城下町長府',42,-37,111,29,'武家屋敷・土塀の町');m.landmark('sumiyoshi',8,'住吉神社',-72,15,87,26);m.landmark('station',0,'下関駅前',1,-100,104,29,'大丸跡の構想・シーモール');x,y=m.point('karato');s.circle(x,y);s.text(x+35,y+7,'唐戸・赤間',28,700,halo=True);s.text(x+35,y+37,'↓ 下の拡大図へ',20,halo=True);x,y=m.pointll(130.916,34.000);s.text(x,y,'JR',23,700,halo=True);x,y=m.pointll(130.995,33.973);s.text(x,y,'関門海峡',27,700,'middle');north(s,35,140);inset=(20,850,640,298);subtitle_y=840
 else:
  m.landmark('shin',5,'新下関駅',-48,-110,100,28,'新幹線の入口');m.landmark('chofu',4,'城下町長府',60,-15,117,28,'武家屋敷・土塀の町');m.landmark('sumiyoshi',8,'住吉神社',-70,18,90,27);m.landmark('station',0,'下関駅前',-43,-99,108,29,'大丸跡の構想・シーモール');x,y=m.point('karato');s.circle(x,y);s.text(x+42,y-5,'唐戸・赤間',29,700,halo=True);s.text(x+42,y+27,'右の拡大図へ →',20,halo=True);x,y=m.pointll(130.910,33.989);s.text(x,y,'JR',23,700,halo=True);x,y=m.pointll(130.997,33.970);s.text(x,y,'関門海峡',30,700,'middle');north(s,42,150);inset=(787,169,368,328);subtitle_y=140
 s.rect(*inset,PAPER,2,9);s.text(inset[0]+5,subtitle_y,'唐戸・赤間を拡大',25,700);mi=Map(s,(130.9395,33.9524,130.953,33.9626),inset,'karato-water');mi.route(['aquarium','market','akama'],'walk')
 if mobile:mi.landmark('aquarium',2,'海響館',-62,-98,89,26);mi.landmark('market',1,'唐戸市場',-9,-95,88,26);mi.landmark('akama',3,'赤間神宮',48,-69,89,26)
 else:mi.landmark('aquarium',2,'海響館',-16,-92,90,25);mi.landmark('market',1,'唐戸市場',-16,-116,83,25);mi.landmark('akama',3,'赤間神宮',27,-55,89,25)
 if mobile:s.text(25,1190,'水色の破線＝新しい周回便の案',25,700);s.text(25,1225,'既存JR・バス＋徒歩を土台に、乗り継ぎを整える。',20);credit(s,1252)
 else:
  for yy,tt,sz,ww in [(555,'水色の破線',25,700),(590,'新しい周回便の案',25,700),(632,'JR・路線バスを土台に、',21,500),(665,'名所をひとめぐり。',21,500),(733,'夜は駅前の食・遊びへ。',23,700),(770,'帰路は予約前に確認。',21,500)]:s.text(797,yy,tt,sz,ww)
  s.path('M30 868 H1145',INK,1);s.text(30,906,'乗降場所・道路経路・便数・運行時間は、交通事業者と協議する企画案です。',21);credit(s,949)
 s.save('map-city'+('-mobile' if mobile else '')+'.svg')
def kanmon(mobile=False):
 w,h=(680,1160) if mobile else (1180,1010);s=SVG(w,h,'関門広域の回遊イメージ','実際の海岸線をもとに、下関・唐戸・門司港・門司・小倉を結ぶ。JRは国土地理院の鉄道線、船とバスは接続を簡略化。夜間運行や帰宅保証を示さない。');s.text(25,44,'03 / 海峡ごと、楽しもう。',32,700);s.text(25,79,'下関 × 門司港 × 小倉 / ONE KANMON',20)
 rect,bbox=((10,105,660,850),(130.864,33.871,131.014,34.020)) if mobile else ((25,104,1130,776),(130.840,33.875,131.047,34.018));m=Map(s,bbox,rect,'kanmon-water',True);m.route(['station',(130.932,33.953),'karato']);m.route(['karato',(130.9522,33.948),'mojiko'],'ferry')
 if mobile:
  m.landmark('shin',5,'新下関駅',-75,-100,97,29);m.landmark('station',0,'下関駅前',-95,-100,103,29,'夜の食・遊びの拠点案');m.landmark('karato',1,'唐戸',1,-123,96,29,'昼の市場・海の体験');m.landmark('mojiko',6,'門司港',46,28,111,30,'港のまち歩き');m.landmark('kokura',7,'小倉',16,-130,105,30,'城・商い・文化');x,y=m.point('moji');s.circle(x,y);s.text(x+15,y+30,'門司駅',27,700,halo=True)
  for lon,lat,tt in [(130.987,34.010,'本州'),(130.988,33.891,'九州'),(130.942,33.933,'関門海峡')]:x,y=m.pointll(lon,lat);s.text(x,y,tt,27,700,'middle')
  north(s,40,130);s.rect(25,250,183,142,PAPER,1,5);s.path('M40 280 H77',INK,4);s.path('M40 280 H77',PAPER,1.3);s.text(91,287,'鉄道',21);s.path('M40 326 H77',INK,3.5);s.text(91,333,'バス',21);s.path('M40 371 H77',INK,4,'3 9');s.text(91,378,'連絡船',21);s.text(25,988,'船で渡る。鉄道で広げる。',29,700);s.text(25,1027,'下関 → 唐戸 → 門司港 → 小倉へ。',23);s.text(25,1063,'夜の帰路は、宿と終便に合わせて設計。',23);credit(s,1108)
 else:
  m.landmark('shin',5,'新下関駅',-99,-63,100,27);m.landmark('station',0,'下関駅前',-143,-88,123,31,'夜の食・遊びの拠点案');m.landmark('karato',1,'唐戸',37,-154,113,30,'昼の市場・海の体験');m.landmark('mojiko',6,'門司港',115,6,124,31,'港のまち歩き');m.landmark('kokura',7,'小倉',-84,-160,117,31,'城・商い・文化');x,y=m.point('moji');s.circle(x,y);s.text(x+22,y+5,'門司駅',27,700,halo=True)
  for lon,lat,tt in [(130.990,34.011,'本州'),(130.987,33.903,'九州'),(130.918,33.929,'関門海峡')]:x,y=m.pointll(lon,lat);s.text(x,y,tt,30,700,'middle')
  x,y=m.pointll(130.953,33.949);s.text(x+13,y,'連絡船',22,700,halo=True);x,y=m.pointll(130.951,33.886);s.text(x,y,'JR 在来線でつながる',24,700,halo=True);north(s,45,149);s.rect(50,245,235,161,PAPER,1,5);s.path('M70 280 H122',INK,4);s.path('M70 280 H122',PAPER,1.3);s.text(140,287,'既存の鉄道',22);s.path('M70 329 H122',INK,3.5);s.text(140,336,'路線バス',22);s.path('M70 378 H122',INK,4,'3 9');s.text(140,385,'連絡船',22);s.path('M25 891 H1155',INK,1);s.text(25,933,'門司駅と門司港駅は別の駅。船・鉄道・バスは夜間の運行を保証するものではありません。',21);credit(s,967)
 s.save('map-kanmon'+('-mobile' if mobile else '')+'.svg')
def building(mobile=False):
 w,h=(680,1150) if mobile else (1180,970);s=SVG(w,h,'建物の立体フロア構成案','B1から5Fの配置案。日常の食、夜の市場、日本の工芸、ゲーム・IP、音楽と物語、暮らしと仕事。屋上は別途調査する将来案。実測図・設計図ではない。');s.text(25,43,'01 / 建物の中に、小さなまち。',30,700);s.text(25,78,'食べる → つくる → 遊ぶ → 物語に入る',21)
 names=[('5F','暮らし・仕事','LOCAL LIFE / WORK'),('4F','音楽とものがたり','LIVE & EXPERIENCE'),('3F','ゲーム・IP','POP CULTURE NIGHT'),('2F','工芸と夜の買い物','JAPAN NIGHT'),('1F','夜の食と旅の案内','NIGHT MARKET / TRIP'),('B1','食材とお持ち帰り','EVERYDAY FOOD')]
 for i,(floor,title,eng) in enumerate(names):
  y=(120+i*141) if mobile else (122+i*116)
  if mobile:a,b,c,d=(122,y),(323,y+38),(234,y+90),(33,y+52);tx=357
  else:a,b,c,d=(224,y),(555,y+47),(407,y+109),(76,y+62);tx=635
  for pts,color in [([d,c,(c[0],c[1]+10),(d[0],d[1]+10)],PAPER),([b,c,(c[0],c[1]+10),(b[0],b[1]+10)],'#C5A6E8'),([a,b,c,d],PAPER)]:s.p.append(f'<polygon points="{" ".join(f"{x},{v}" for x,v in pts)}" fill="{color}" stroke="{INK}" stroke-width="2.2"/>')
  s.text(d[0]+27,d[1]+13,floor,25,700)
  if i in (1,2,3,4):s.vignette({1:3,2:2,3:1,4:0}[i],a[0]+(8 if mobile else 32),y+1,151 if mobile else 226,75 if mobile else 90)
  else:
   s.path(f'M{a[0]+30},{y+29} l80,13 -34,20 -80,-13 Z',INK,2,fill='#C5A6E8');s.path(f'M{a[0]+139},{y+45} l45,7 -23,13 -45,-7 Z',INK,2,fill=PAPER)
  s.path(f'M{b[0]+5},{b[1]+7} H{tx-20}',INK,1.4);s.text(tx,y+30,floor+' 案',23,700)
  if mobile:
   for k,t in enumerate(title.split('と')):s.text(tx,y+68+k*32,t,27,700)
  else:s.text(tx,y+68,title,30,700);s.text(tx,y+99,eng,18,400)
 if mobile:s.rect(25,1002,630,114,PAPER,1.5,5,'7 6');s.text(42,1037,'ROOFTOP / 将来の検討案',22,700);s.text(42,1071,'KANMON SKY：構造・眺望・音・避難を調査。',20);s.text(42,1100,'実測図ではありません。全館同時開業は前提にしません。',17)
 else:s.rect(25,853,1130,87,PAPER,1.5,5,'7 6');s.text(44,886,'ROOFTOP / KANMON SKY は将来の検討案',24,700);s.text(44,920,'構造・眺望・音・避難を調査。これは機能の配置案で、実測図や設計図ではありません。',20)
 s.save('map-building'+('-mobile' if mobile else '')+'.svg')
if __name__=='__main__':
 for mobile in (False,True):building(mobile);city(mobile);kanmon(mobile)
 print('Wrote six illustrated SVG maps.')
