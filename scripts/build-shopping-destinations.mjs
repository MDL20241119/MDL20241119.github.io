import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {validPoint,cityAt} from '../oita-mobility/v2/model.mjs';

export function mapCoordinates(url){
  const text=decodeURIComponent(url??'');let m;
  const markers=[...text.matchAll(/!3d(-?[\d.]+)!4d(-?[\d.]+)/g)];
  if(markers.length){m=markers.at(-1);return {lat:Number(m[1]),lon:Number(m[2]),coordinatePrecision:'official_map_marker'};}
  if((m=text.match(/@(-?[\d.]+),(-?[\d.]+)/)))return {lat:Number(m[1]),lon:Number(m[2]),coordinatePrecision:'official_map_center'};
  if((m=text.match(/[?&](?:ll|center|q|query)=(-?[\d.]+),\s*(-?[\d.]+)/)))return {lat:Number(m[1]),lon:Number(m[2]),coordinatePrecision:'official_map_center'};
  if((m=text.match(/!2d(-?[\d.]+)!3d(-?[\d.]+)/)))return {lat:Number(m[2]),lon:Number(m[1]),coordinatePrecision:'official_map_viewport'};
  throw Error('公式地図から座標を確認できません: '+url);
}
const clean=s=>String(s??'').normalize('NFKC').replace(/\(Google map\)/ig,'').replace(/^〒[\d-]+\s*/,'').replace(/\s+/g,' ').trim();
const nameKey=s=>clean(s).replace(/\s/g,'');

export function buildShops(snapshot,features){
  const result=[],codes=[...features].sort((a,b)=>b.properties.name.length-a.properties.name.length);
  for(const record of snapshot.records){
    const p={...record,name:clean(record.name),address:clean(record.address),category:'shopping',source:'各店舗の公式案内'};
    if(p.mapUrl){
      Object.assign(p,mapCoordinates(p.mapUrl));
      p.coordinateEvidence=p.mapUrl;p.checkedAt=snapshot.checkedAt;p.retrievedAt=snapshot.checkedAt;p.needsCoordinateConfirmation=true;
      p.positionNote=p.coordinatePrecision==='official_map_marker'?'公式地図の施設位置。入口・歩行経路は未確認です。':'公式地図の概略位置。建物の入口・歩行経路は未確認です。';
      delete p.mapUrl;
    }
    p.openingHours=clean(p.openingHours)||null;
    p.url=p.sourceUrl??p.url;p.sourceUrl=p.url;
    const area=codes.find(f=>p.address.includes(f.properties.name)||p.city===f.properties.name);
    if(!area||!validPoint(p)||!p.name||!p.sourceUrl?.startsWith('https://'))throw Error('店舗情報の不足: '+p.name);
    p.city=area.properties.name;p.municipalityCode=area.properties.code;
    p.shopType??=p.name.includes('HIヒロセ')?'homecenter':'supermarket';
    const located=cityAt(p,features);
    if(located&&located.code!==p.municipalityCode)throw Error('住所と地図の市町村が不一致: '+p.name+' '+p.city+' / '+located.name);
    if(!located)throw Error('公式地図の位置が市町村境界の外: '+p.name);
    const same=result.find(q=>q.sourceUrl===p.sourceUrl||q.city===p.city&&nameKey(q.name)===nameKey(p.name));
    if(same){const id=same.id;Object.assign(same,p,{id});}else result.push(p);
  }
  if(new Set(result.map(p=>p.id)).size!==result.length)throw Error('店舗IDが重複しています');
  return result;
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){
  const root=new URL('../oita-mobility/',import.meta.url),output=new URL('access/destinations.json',root);
  const snapshot=JSON.parse(fs.readFileSync(new URL('access/shopping-sources.json',root),'utf8'));
  const features=JSON.parse(fs.readFileSync(new URL('gaps/data/municipalities.geojson',root),'utf8')).features;
  const current=JSON.parse(fs.readFileSync(output,'utf8'));
  const shops=buildShops(snapshot,features),destinations=[...current.filter(p=>p.category!=='shopping'),...shops];
  const text=JSON.stringify(destinations,null,2)+'\n';
  if(process.argv.includes('--check')){if(fs.readFileSync(output,'utf8')!==text)throw Error('destinations.jsonを再生成してください');}
  else fs.writeFileSync(output,text);
  console.log(JSON.stringify({destinations:destinations.length,shops:shops.length,municipalities:new Set(shops.map(p=>p.city)).size,byType:Object.fromEntries([...new Set(shops.map(p=>p.shopType))].map(t=>[t,shops.filter(p=>p.shopType===t).length]))}));
}
