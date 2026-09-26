import ConsoleApp from './console';
import {seedState} from '@/lib/model';
export const dynamic='force-dynamic';
export default function Home(){return <ConsoleApp guest initialState={seedState()}/>;}
