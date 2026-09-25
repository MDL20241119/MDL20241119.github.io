import {browserPrincipal} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {State,data,publicProposal,ownReservations,stops} from '@/lib/integration/core';
import {inputDate} from '@/lib/model';
import Connections from './view';
export const dynamic='force-dynamic';
export default async function Page(){const p=await browserPrincipal();const s=await readState(p.workspace) as State;return <Connections date={inputDate(s.clock).slice(0,10)} reservations={ownReservations(s,p).map(r=>({id:r.ticketId,start:r.trip?.start??null,from:stops.find(x=>x.id===r.fromStop)?.name??'乗る場所を確認してください',to:stops.find(x=>x.id===r.toStop)?.name??'降りる場所を確認してください',count:r.count,status:r.status,cancellable:r.status==='reserved'&&!!r.trip&&r.trip.start>=s.clock}))} proposals={data(s).proposals.filter(a=>a.subject===p.subject).map(publicProposal).reverse()}/>;}
