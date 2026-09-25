import {browserPrincipal} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {State,data,publicProposal} from '@/lib/integration/core';
import {inputDate} from '@/lib/model';
import Connections from './view';
export const dynamic='force-dynamic';
export default async function Page(){const p=await browserPrincipal();const s=await readState(p.workspace) as State;return <Connections date={inputDate(s.clock).slice(0,10)} proposals={data(s).proposals.filter(a=>a.subject===p.subject).map(publicProposal).reverse()}/>;}
