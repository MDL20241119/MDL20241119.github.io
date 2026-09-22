import test from 'node:test';
import assert from 'node:assert/strict';
import {indexShapes,geometryForLeg,attachRouteGeometry} from '../oita-mobility/v2/route-geometry.mjs';
import {matchingDestinations,resolveDestination,searchText} from '../oita-mobility/v2/destinations.mjs';
import {mapCoordinates} from '../scripts/build-shopping-destinations.mjs';

const points=[[33,131],[33.001,131.005],[33,131.01],[33,131.02]];
const shapes=indexShapes([{id:'feed',tables:{shapes:points.map(([lat,lon],i)=>({shape_id:'shape',shape_pt_lat:String(lat),shape_pt_lon:String(lon),shape_pt_sequence:String(i),shape_dist_traveled:String(i*100)}))}}]);
const calls=points.map(([lat,lon],i)=>({stopKey:'s'+i,stop_sequence:String(i+1),shape_dist_traveled:String(i*100)}));
const network={trips:[{key:'trip@20260922',feed:'feed',shape:'shape',calls}],stops:Object.fromEntries(points.map(([lat,lon],i)=>['s'+i,{lat,lon}]))};
const leg={mode:'bus',tripKey:'trip@20260922',boardSequence:'2',alightSequence:'4',from:network.stops.s1,to:network.stops.s3};
test('Map clips the exact selected GTFS trip to boarding and alighting stops',()=>{assert.deepEqual(geometryForLeg(leg,network,shapes).points,points.slice(1));assert.equal(geometryForLeg(leg,network,shapes).kind,'gtfs-shape');});
test('Map aligns unmeasured stops in trip order, not reversed endpoints',()=>{const n=structuredClone(network);n.trips[0].calls.forEach(c=>delete c.shape_dist_traveled);assert.deepEqual(geometryForLeg(leg,n,shapes).points,points.slice(1));assert.equal(geometryForLeg({...leg,boardSequence:'4',alightSequence:'2'},n,shapes).kind,'approximate');});
test('A stop nearer the return road cannot jump over the intervening outbound calls',()=>{
 const route=[[33,131],[33,131.01],[33.001,131.02],[33.00005,131.01],[33,131.03]];
 const s=indexShapes([{id:'loop-feed',tables:{shapes:route.map(([lat,lon],i)=>({shape_id:'loop',shape_pt_lat:String(lat),shape_pt_lon:String(lon),shape_pt_sequence:String(i)}))}}]);
 const stopPoints=[route[0],route[3],route[2],route[3],route[4]];
 const n={stops:Object.fromEntries(stopPoints.map(([lat,lon],i)=>['s'+i,{lat,lon}])),trips:[{key:'loop-trip',feed:'loop-feed',shape:'loop',calls:stopPoints.map((_,i)=>({stopKey:'s'+i,stop_sequence:String(i)}))}]};
 const g=geometryForLeg({mode:'bus',tripKey:'loop-trip',boardSequence:'1',alightSequence:'3',from:n.stops.s1,to:n.stops.s3},n,s);
 assert.equal(g.kind,'gtfs-shape');
 assert(g.points.some(p=>p[0]===33.001&&p[1]===131.02),'Route must retain the outbound turn before returning to the repeated stop');
});
test('Missing shapes, unrelated trips and poor alignment remain explicitly approximate',()=>{assert.equal(geometryForLeg(leg,network,new Map()).kind,'approximate');assert.equal(geometryForLeg({...leg,tripKey:'other'},network,shapes).kind,'approximate');assert.equal(geometryForLeg({...leg,from:{lat:34,lon:132}},network,shapes).kind,'approximate');});
test('Walking is never represented as a street-accurate route',()=>{const walk={...leg,mode:'walk'};assert.equal(geometryForLeg(walk,network,shapes).kind,'walk-estimate');const r=attachRouteGeometry({outbound:{path:[leg]},inbound:{path:[walk]}},network,shapes);assert.equal(r.outbound.path[0].geometry.kind,'gtfs-shape');assert.equal(r.inbound.path[0].geometry.kind,'walk-estimate');});
test('Official map markers take precedence over viewport centers; no coordinates are fabricated',()=>{assert.deepEqual(mapCoordinates('https://www.google.com/maps/@33.1,131.1,15z/data=!3d33.2!4d131.2'),{lat:33.2,lon:131.2,coordinatePrecision:'official_map_marker'});assert.equal(mapCoordinates('https://maps.google.com/?ll=33.1,131.1').lat,33.1);assert.equal(mapCoordinates('https://maps.google.com/embed?pb=!2d131.2!3d33.2').lon,131.2);assert.throws(()=>mapCoordinates('https://example.org/unknown'));});
const places=[{id:'a',name:'コスモス A店',brand:'コスモス',category:'shopping',shopType:'drugstore',city:'大分市',address:'大分市下郡1-1',lat:33,lon:131},{id:'b',name:'新鮮市場 B店',category:'shopping',shopType:'supermarket',city:'別府市',address:'別府市北浜',lat:33.01,lon:131}];
test('Destination search supports kana, full-width text, multiple tokens, address and shop type',()=>{assert.equal(searchText('ｺｽﾓｽ'),searchText('こすもす'));assert.equal(matchingDestinations(places,{query:'こすもす 下郡'})[0].id,'a');assert.deepEqual(matchingDestinations(places,{category:'shopping',type:'supermarket'}).map(p=>p.id),['b']);assert.equal(matchingDestinations(places,{query:'ドラッグストア'})[0].id,'a');});
test('Ambiguous destination names never silently select the wrong shop',()=>{assert.equal(resolveDestination('コスモス A店',[places[0],{...places[0],id:'c',city:'別府市'}]),null);assert.equal(resolveDestination('コスモス A店（大分市）',places).id,'a');});
test('All matching destinations remain available rather than a fixed first eight',()=>{const many=Array.from({length:45},(_,i)=>({...places[0],id:String(i),name:'コスモス '+i+'店'}));assert.equal(matchingDestinations(many,{category:'shopping'}).length,45);});
