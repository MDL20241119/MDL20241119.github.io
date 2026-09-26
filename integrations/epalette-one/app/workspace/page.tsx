import ConsoleApp from '../console';
import {requireChatGPTUser} from '../chatgpt-auth';
export const dynamic='force-dynamic';
export default async function SavedWorkspace(){await requireChatGPTUser('/workspace');return <ConsoleApp/>;}
