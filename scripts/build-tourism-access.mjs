import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {importGTFS,buildNetwork} from '../oita-mobility/lab/gtfs.mjs';
import {directCalls,packAccess} from '../oita-tourism/access-model.mjs';
const root=new URL('../',import.meta.url),read=async p=>JSON.parse(await fs.readFile(new URL(p,root),'utf8'));
const tourism=await read('oita-tourism/data/tourism.json'),map=await read('oita-mobility/data/map-data.json'),catalog=await read('oita-mobility/data/gtfs/catalog.json');
const dates=map.meta.dates,calls=[],feeds=[];
for(const item of catalog){const raw=await fs.readFile(new URL('oita-mobility/data/gtfs/'+item.file,root));const hash=createHash('sha256').update(raw).digest('hex');if(hash!==item.sha256)throw Error('GTFS hash mismatch: '+item.file);
 const entry=map.feeds.find(f=>f.sha256===hash);if(!entry)throw Error('Shared feed ID missing');
 const f=await importGTFS(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength),item.name,entry.id);
 feeds.push({id:entry.id,name:item.name,sha256:hash,sourceUrl:item.source,validFrom:entry.validFrom,validTo:entry.validTo});
 for(let day=0;day<dates.length;day++){const date=dates[day];if(date<entry.validFrom.replaceAll('-','')||date>entry.validTo.replaceAll('-',''))continue;calls.push(...directCalls(buildNetwork([f],date),tourism.anchors,entry,day));}
}
const output={schemaVersion:1,method:'同一便で通常乗降できる停留所の組合せ。基準点から直線300m以内。鉄道・乗換・徒歩経路は含まない。',radius:300,dates,sourceRetrievedAt:map.meta.retrievedAt,feeds,calls};
await fs.writeFile(new URL('oita-tourism/data/access.json',root),JSON.stringify(packAccess(output))+'\n');console.log(JSON.stringify({calls:calls.length,feeds:feeds.length,dates}));
