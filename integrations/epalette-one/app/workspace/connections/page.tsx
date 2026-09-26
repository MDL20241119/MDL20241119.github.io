import {requireChatGPTUser} from '@/app/chatgpt-auth';
import {browserPrincipal} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {data,ownReservations,publicProposal,stops,State} from '@/lib/integration/core';
import {inputDate} from '@/lib/model';
import Connections from '@/app/connections/view';
export const dynamic='force-dynamic';
export default async function Page(){await requireChatGPTUser('/workspace/connections');const p=await browserPrincipal(),s=await readState(p.workspace) as State;return <Connections date={inputDate(s.clock).slice(0,10)} reservations={ownReservations(s,p).map(r=>({id:r.ticketId,start:r.trip?.start??null,from:stops.find(x=>x.id===r.fromStop)?.name??'場所未確認',to:stops.find(x=>x.id===r.toStop)?.name??'場所未確認',count:r.count,status:r.status,cancellable:r.status==='reserved'&&!!r.trip&&r.trip.start>=s.clock}))} proposals={data(s).proposals.filter(a=>a.subject===p.subject).map(publicProposal).reverse()}/>;}
