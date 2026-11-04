import ManualConsole from '../../manual/view';
import {requireChatGPTUser} from '../../chatgpt-auth';
export const dynamic='force-dynamic';
export default async function ManualWorkspace(){await requireChatGPTUser('/workspace/manual');return <ManualConsole guest={false}/>;}
