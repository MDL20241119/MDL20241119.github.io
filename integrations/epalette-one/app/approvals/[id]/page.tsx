import {requireChatGPTUser} from '@/app/chatgpt-auth';
import {browserPrincipal} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {getProposal,State} from '@/lib/integration/core';
import Approval from './view';
export const dynamic='force-dynamic';
export default async function Page({params}:{params:Promise<{id:string}>}){await requireChatGPTUser('/approvals/'+(await params).id);const p=await browserPrincipal();const s=await readState(p.workspace) as State;try{const a=getProposal(s,p,(await params).id);return <Approval id={a.id} csrf={a.csrf} version={s.version} summary={a.summary} status={a.status} expiresAt={a.expiresAt} stale={a.baseVersion!==s.version}/>;}catch{return <main style={{padding:40,fontSize:20}}><h1>確認内容が見つかりません</h1><p>このアカウントで確認できる内容を開いてください。</p><a href="/workspace/connections">連携の画面へ戻る</a></main>;}}
