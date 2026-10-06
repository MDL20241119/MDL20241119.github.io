'use client';
import {newId} from '@/lib/id';
import {useEffect,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,BusFront,CheckCircle2,Clock3,Link2,Zap,ShieldCheck,Copy,Ticket,ChevronDown,MapPin} from 'lucide-react';
import {Collapsible,CollapsibleContent,CollapsibleTrigger} from '@/components/ui/collapsible';
import {integrationStatus} from '@/lib/integration/status';
import {demoAction,demoSavedInTab} from '@/lib/guest-demo';
import {durationRange} from '@/lib/presentation';
import './style.css';
type ProposalView={id:string;status:string;summary:Record<string,unknown>;expiresAt:string};
type ReservationView={id:string;start:string|null;from:string;to:string;count:number;status:string;cancellable:boolean};
export type ConnectionProps={date:string;proposals:ProposalView[];reservations:ReservationView[];guest?:boolean};
const reservationLabels:Record<string,string>={reserved:'予約済み',boarded:'乗車中',alighted:'利用済み',cancelled:'取消済み',unavailable:'確認できません'};
const dateTime=(v:string)=>new Date(v).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',month:'long',day:'numeric',weekday:'short',hour:'2-digit',minute:'2-digit'});
export default function Connections({date,proposals,reservations,guest=false}:ConnectionProps){
 const retry=useRef<{signature:string;key:string}|null>(null),lock=useRef(false);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[charge,setCharge]=useState<any>(null),[selectedDate,setDate]=useState(date),[count,setCount]=useState(1),[candidates,setCandidates]=useState<any[]|null>(null),[copied,setCopied]=useState('');
 async function invoke(name:string,args:unknown):Promise<any>{
  if(guest){const result=demoAction(name,args);if(!demoSavedInTab())throw Error('この端末では保存できません。予約を確定せず、ブラウザーの保存設定を確認してください。');return result;}
  const signature=JSON.stringify({name,args}),key=retry.current?.signature===signature?retry.current.key:newId();retry.current={signature,key};
  const r=await fetch('/api/v1/actions/'+name,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify(args)}),value=await r.json() as any;
  if(!r.ok){if(r.status<500)retry.current=null;throw Error(value.error?.message??'接続を確認してください。');}retry.current=null;return value;
 }
 async function run(fn:()=>Promise<void>){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'接続を確認してください。');}finally{lock.current=false;setBusy(false);}}
 async function search(){const r=await invoke('search_trips',{date:selectedDate,fromStop:'oita-station',toStop:'community-hub',count});setCandidates(r.trips);}
 useEffect(()=>{void run(search);},[]);
 const pending=proposals.filter(p=>p.status==='pending'&&p.expiresAt>new Date().toISOString());
 const home=guest?'/':'/workspace',approvalBase=guest?'/try/approvals/':'/approvals/';
 return <div className="integration-shell"><a className="skip-link" href="#reservation-main">本文へ移動</a><header className="integration-top"><a href={home} className="back-link"><ArrowLeft/>今日へ</a><a href={home} className="integration-brand" aria-label="e-Palette ONE ホーム">e-Palette <span>ONE</span></a><span className="integration-mode">{guest?'ログイン不要':'保存用管理画面'}</span></header>
 <main id="reservation-main" className="integration-main">
 <div className="integration-note"><ShieldCheck/><span>{guest?'体験用の予約です。このタブ内にだけ保存します。':'検証用の予約です。'} 実際の送迎・課金はありません。</span></div>
 <div className="integration-heading"><div><p className="eyebrow">お出かけの準備を、かんたんに。</p><h1>乗車予約</h1></div><ol className="compact-steps" aria-label="予約の手順"><li className="current"><span>1</span>便を選ぶ</li><li><span>2</span>内容を確認</li><li><span>3</span>予約完了</li></ol></div>
 {error&&<div className="integration-error" role="alert">{error}</div>}
 {pending.length>0&&<section className="integration-card pending-card"><div className="integration-section-title"><Clock3/><h2>まだ確定していない内容</h2><span>{pending.length}件</span></div>{pending.map(p=><a className="proposal-row" href={approvalBase+p.id} key={p.id}><div><strong>{String(p.summary.title)}</strong><small>内容を確認して、確定または見送り</small></div><ArrowRight/></a>)}</section>}
 <div className="reservation-layout"><section className="integration-card search-card" aria-labelledby="search-title">
 <div className="integration-section-title"><BusFront/><h2 id="search-title">乗れる便を探す</h2></div>
 <div className="route-preview"><div><span>乗る</span><strong>大分駅前</strong></div><ArrowRight aria-hidden="true"/><div><span>降りる</span><strong>地域拠点</strong></div></div>
 <p className="search-caption">この体験版は、上記の区間・無料運行でお試しいただけます。</p>
 <form onSubmit={e=>{e.preventDefault();void run(search);}}><div className="search-fields"><label>利用日<input type="date" required value={selectedDate} onChange={e=>{setDate(e.target.value);setCandidates(null);}}/></label><label>人数<select value={count} onChange={e=>{setCount(Number(e.target.value));setCandidates(null);}}>{Array.from({length:8},(_,i)=><option key={i} value={i+1}>{i+1}人</option>)}</select></label></div><button className="secondary search-submit" disabled={busy} type="submit">{busy?'確認しています…':'この条件で探す'}<ArrowRight/></button></form>
 <div className="search-results" aria-live="polite" aria-busy={busy}>{candidates!==null&&(candidates.length===0?<div className="empty-result"><Clock3/><strong>この条件で乗れる便はありません</strong><p>日付・人数を変えてお探しください。模擬の予定は「今日」の画面で追加できます。</p></div>:<><p className="result-caption">{candidates.length}件の便が見つかりました</p>{candidates.map(t=><article className="candidate-row" key={t.id}><div className="candidate-header"><time>{new Date(t.start).toLocaleTimeString('ja-JP',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit'})}</time><span><CheckCircle2/>空席 {t.available}人</span></div><h3>{t.name}</h3><p>{count}人・合計 <strong>0円</strong> <small>（検証用）</small></p><button disabled={busy} onClick={()=>void run(async()=>{const a=await invoke('prepare_ride_booking',{tripId:t.id,count,fromStop:'oita-station',toStop:'community-hub'});window.location.assign(a.approvalUrl);})}>この便の予約内容を見る<ArrowRight/></button></article>)}</>)}</div>
 </section>
 <aside className="integration-card your-reservations" aria-labelledby="my-reservations"><div className="integration-section-title"><Ticket/><h2 id="my-reservations">あなたの予約</h2></div>{reservations.length===0?<div className="empty-reservations"><Ticket/><strong>まだ予約はありません</strong><p>便を選んで内容を確認すると、ここに表示されます。</p></div>:reservations.slice().reverse().map(r=><article className="reservation-row" key={r.id}><span className={'reservation-status '+(r.status==='cancelled'?'muted':'')}>{reservationLabels[r.status]??'確認できません'}</span><h3>{r.start?dateTime(r.start):'日時を確認してください'}</h3><p>{r.from} → {r.to}<br/>{r.count}人・検証用 0円</p>{r.cancellable?<button className="secondary" disabled={busy} onClick={()=>void run(async()=>{const a=await invoke('prepare_ride_cancellation',{reservationId:r.id});window.location.assign(a.approvalUrl);})}>取消内容を確認<ArrowRight/></button>:r.status==='reserved'?<p>乗車時刻を過ぎた予約は、担当者へ連絡してください。</p>:null}</article>)}</aside></div>
 <Collapsible className="integration-card"><CollapsibleTrigger className="detail-trigger"><span><Zap/>管理者向け：充電の見込みを確認</span><ChevronDown/></CollapsibleTrigger><CollapsibleContent className="expanded-detail"><p>車両の残量と予定から計算します。AIによる数値の推測は行いません。</p><button className="secondary" disabled={busy} onClick={()=>void run(async()=>setCharge(await invoke('get_charge_plan',{vehicleId:'EP-01'})))}>EP-01の充電を確認<ArrowRight/></button>{charge&&<div className="charge-answer" aria-live="polite">{charge.plans?.map((p:any)=><div key={p.stationId}><h3>{p.mode==='ac'?'普通充電':'急速充電'}</h3>{p.valid&&!p.uncertain?<><strong>{durationRange(p.min,p.max)}</strong><p>{dateTime(p.leaveAt)}までに出発</p><span>{p.possible?'間に合う見込み':'開始期限を過ぎています'}</span></>:<p>{p.reason??'条件を確認できません。担当者が確認してください。'}</p>}</div>)}{!charge.plans&&<p>{charge.reason}</p>}<p>模擬の残量・車両仕様による計算です。</p></div>}</CollapsibleContent></Collapsible>
 <Collapsible className="integration-card"><CollapsibleTrigger className="detail-trigger"><span><Link2/>AI・交通サービスとの接続状況</span><ChevronDown/></CollapsibleTrigger><CollapsibleContent className="expanded-detail"><p>体験用の予約は外部APIへ送信しません。外部AIとの接続には、管理者による登録・認証と個別の検証が必要です。</p><div className="endpoint-row"><label>MCP</label><code>/mcp</code><button className="secondary" onClick={()=>void navigator.clipboard.writeText(window.location.origin+'/mcp').then(()=>setCopied('MCPのURLをコピーしました')).catch(()=>setCopied('コピーできませんでした。URLを選択してコピーしてください。'))}><Copy/>URLをコピー</button></div><div className="endpoint-row"><label>A2A</label><code>/a2a</code></div><p aria-live="polite">{copied}</p><a className="back-link" href="/api/v1/openapi" target="_blank" rel="noreferrer">通常APIの定義を開く<ArrowRight/></a><div className="standards-list">{integrationStatus.map(s=><div key={s.name}><h3>{s.name} <small>{s.version}</small></h3><strong>{s.connection}</strong><p>{s.scope}</p><small>{s.implementation} / {s.verification}</small></div>)}</div><p>外部接続の確認記録：AI 0件・交通事業者 0件・QR認証ハブ 0件。</p></CollapsibleContent></Collapsible>
 </main></div>;
}
