'use client';
import {useEffect,useState} from 'react';
import {demoState,demoPrincipal} from '@/lib/guest-demo';
import {getProposal,Proposal} from '@/lib/integration/core';
import Approval from '@/app/approvals/[id]/view';
export default function GuestApproval({id}:{id:string}){
 const [current,setCurrent]=useState<{proposal:Proposal;version:number}|null>(null),[missing,setMissing]=useState(false);
 useEffect(()=>{try{const s=demoState();setCurrent({proposal:getProposal(s,demoPrincipal,id),version:s.version});}catch{setMissing(true);}},[id]);
 if(missing)return <main className="confirmation-main"><h1>確認内容が見つかりません</h1><p>体験用の予約は、このタブの中に保存されます。乗車予約から、もう一度お選びください。</p><a className="button-link" href="/connections">乗車予約に戻る</a></main>;
 if(!current)return <main className="boot" role="status">予約内容を開いています…</main>;
 const a=current.proposal;return <Approval guest id={id} csrf={a.csrf} version={current.version} summary={a.summary} status={a.status} expiresAt={a.expiresAt} stale={a.baseVersion!==current.version}/>;
}
