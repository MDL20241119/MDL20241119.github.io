import {requireChatGPTUser} from '@/app/chatgpt-auth';
import {authorizeOwner} from '@/lib/board-server';
import SharingSettings from './settings';
export const dynamic='force-dynamic';
export default async function Page(){await requireChatGPTUser('/admin/sharing');try{await authorizeOwner();return <SharingSettings/>}catch{return <main style={{padding:40}}><h1>この設定は管理者専用です。</h1><a href="/">ボードへ戻る</a></main>}}
