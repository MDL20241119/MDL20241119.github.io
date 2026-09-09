import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {accessShareUrl,publicGapProfile} from '../oita-mobility/assets/share-state.mjs';
import {defaultProfile,validateProfile} from '../oita-mobility/gaps/engine.mjs';
import {exportFeed,importGTFS} from '../oita-mobility/lab/gtfs.mjs';
import {unzip} from '../oita-mobility/lab/io.mjs';

// The receiver can reproduce numeric conditions without getting personal notes.
const profile=defaultProfile('44202',['public.zip']);
Object.assign(profile,{name:'PRIVATE_NAME',note:'PRIVATE_NOTE',distanceM:650,minimumTrips:8,destinations:['public-facility'],unknownExtension:'PRIVATE_EXTRA'});
const before=structuredClone(profile),shared=publicGapProfile(profile);
assert.doesNotThrow(()=>validateProfile(shared));
assert.equal(shared.distanceM,650);assert.equal(shared.minimumTrips,8);
assert.deepEqual(shared.destinations,['public-facility']);
assert(!JSON.stringify(shared).includes('PRIVATE_'));
shared.files.push('receiver-change.zip');
assert.deepEqual(profile,before,'Preparing a shared link must not alter local records');

const url=new URL(accessShareUrl('https://mobilitydlab.com/oita-mobility/accessibility.html?q=PRIVATE_SEARCH&tracking=PRIVATE_TRACKING#PRIVATE_FRAGMENT',{category:'hospital',city:'別府市'}));
assert.equal(url.pathname,'/oita-mobility/accessibility.html');
assert.deepEqual([...url.searchParams],[['category','hospital'],['city','別府市']]);
assert.equal(url.hash,'');assert(!url.href.includes('PRIVATE_'));
assert.equal(accessShareUrl(url.href,{category:'all',city:'all'}),'https://mobilitydlab.com/oita-mobility/accessibility.html');

// Exercise the actual bundled data and ZIP exporter, including a notice collision.
const base=new URL('../oita-mobility/',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('data/gtfs/catalog.json',base),'utf8'));
assert.equal(catalog.length,16);
for(const entry of catalog){
  const bytes=await readFile(new URL('data/gtfs/'+entry.file,base));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),entry.sha256);
  assert.equal(entry.license,'CC BY 4.0');assert(entry.licenseUrl.startsWith('https://creativecommons.org/'));
}
const entry=catalog[0],bytes=await readFile(new URL('data/gtfs/'+entry.file,base));
const feed=await importGTFS(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),entry.name,'f1');
Object.assign(feed,{source:entry.source,catalog:entry.catalog,retrieved:entry.retrieved,license:entry.license,licenseUrl:entry.licenseUrl,attribution:entry.attribution});
feed.name='GTFS,"確認用".zip';
feed.extra={...feed.extra,'MDL-EXPORT-NOTICE.md':Array.from(new TextEncoder().encode('Upstream notice must survive'))};
const out=await unzip(await exportFeed(feed).arrayBuffer()),decode=x=>new TextDecoder().decode(x);
assert.equal(decode(out['MDL-EXPORT-NOTICE.md']),'Upstream notice must survive');
const notice=decode(out['MDL-EXPORT-NOTICE-2.md']);
for(const value of [entry.source,entry.catalog,entry.licenseUrl,'CC BY 4.0','変換・編集','公式ダイヤ'])assert(notice.includes(value),value);
const roundTrip=await importGTFS(await exportFeed(feed).arrayBuffer(),entry.name,'f1');
assert(isDeepStrictEqual(roundTrip.tables,feed.tables),'Added notices must not change timetable records');
assert.equal(decode(new Uint8Array(roundTrip.extra['MDL-EXPORT-NOTICE.md'])),'Upstream notice must survive');
const unknown=await unzip(await exportFeed({tables:{},extra:{}}).arrayBuffer());
assert(decode(unknown['MDL-EXPORT-NOTICE.md']).includes('未確認'));
assert(!decode(unknown['MDL-EXPORT-NOTICE.md']).includes('CC BY 4.0'));
console.log('PASS: private fields excluded; conditions preserved; 16 source hashes unchanged; GTFS attribution and original notices retained.');
