'use client';
import {useEffect,useState} from 'react';
import {demoState,demoPrincipal,DEMO_EVENT} from '@/lib/guest-demo';
import {inputDate} from '@/lib/model';
import {data,ownReservations,publicProposal,stops} from '@/lib/integration/core';
import Connections,{ConnectionProps} from './view';
export default function GuestConnections(){
 const [props,setProps]=useState<ConnectionProps|null>(null);
 useEffect(()=>{const refresh=()=>{const s=demoState();setProps({guest:true,date:inputDate(s.clock).slice(0,10),proposals:data(s).proposals.map(publicProposal),reservations:ownReservations(s,demoPrincipal).map(r=>({id:r.ticketId,start:r.trip?.start??null,from:stops.find(x=>x.id===r.fromStop)?.name??'場所未確認',to:stops.find(x=>x.id===r.toStop)?.name??'場所未確認',count:r.count,status:r.status,cancellable:r.status==='reserved'&&!!r.trip&&r.trip.start>=s.clock}))});};refresh();window.addEventListener(DEMO_EVENT,refresh);return()=>window.removeEventListener(DEMO_EVENT,refresh);},[]);
 return props?<Connections {...props}/>:<main className="boot" role="status">乗車予約を開いています…</main>;
}
