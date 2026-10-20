import ManualConsole from './view';
import {seedState} from '@/lib/model';
export const dynamic='force-dynamic';
export default function ManualReview(){return <ManualConsole guest initialState={seedState()}/>;}
