import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DEFAULT_CITY,ROLES,roleLinks} from '../oita-mobility/v2/audiences.mjs';
const base='https://mobilitydlab.com/oita-mobility/';
const links=(...input)=>roleLinks(...input).map(([label,url])=>[label,new URL(url,base)]);

test('the four distinct workflows open actual tools with the selected area',()=>{
 assert.equal(DEFAULT_CITY,'44201');
 assert.deepEqual(Object.keys(ROLES),['city','operator','resident','tourist']);
 assert.equal(new Set(Object.values(ROLES).map(r=>r.title)).size,4);
 const [municipal,detail]=links('city','44202');
 assert.equal(municipal[1].searchParams.get('city'),'44202');
 assert.equal(municipal[1].hash,'#atlas-time-gaps');
 assert.equal(detail[1].searchParams.get('view'),'detail');
 assert.equal(links('operator')[0][1].pathname,'/oita-mobility/ridership.html');
 assert.equal(links('operator')[1][1].hash,'#design');
 assert.equal(links('resident')[0][1].pathname,'/oita-mobility/journey.html');
 assert.equal(links('tourist')[0][1].pathname,'/oita-tourism/');
});
test('resident selection and intermunicipal mode carry through, without coordinates',()=>{
 const url=links('resident','44201',true,{id:'mhlw-123',lat:33,lon:131})[0][1];
 assert.equal(url.hash,'#people-map');
 assert.deepEqual(Object.fromEntries(url.searchParams),{city:'44201',cross:'1',destination:'mhlw-123'});
 assert.equal(links('resident','bad',false)[0][1].searchParams.get('city'),'44201');
});
test('tourism access gets the selected place and starts in Oita, not a default unrelated city',()=>{
 const url=links('tourist','44201',true,{id:'beppu-jigoku'})[0][1];
 assert.equal(url.hash,'#access');
 assert.equal(url.searchParams.get('from'),'oita-station');
 assert.equal(url.searchParams.get('place'),'beppu-jigoku');
 assert.equal(links('tourist')[0][1].searchParams.get('place'),'oita-takasaki');
});
test('document places interactive map before actions and labels distinct modes',async()=>{
 const html=await readFile(new URL('../oita-mobility/audiences.html',import.meta.url),'utf8');
 for(const role of Object.keys(ROLES)) assert.match(html,new RegExp('data-role="'+role+'"'));
 assert.ok(html.indexOf('id="audience-map"')<html.indexOf('id="primary-link"'));
 assert.match(html,/id="area"[^]*value="44201"/);
 assert.match(html,/id="cross"/);
 assert.match(html,/鉄道の時刻・乗継はこの地図では判定しません/);
});
